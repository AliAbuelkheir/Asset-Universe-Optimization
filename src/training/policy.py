"""Custom masked PPO policy for month-level asset risk scoring."""

from __future__ import annotations

from typing import Any, Optional

import numpy as np
import torch as th
from gymnasium import spaces
from torch import nn
from torch.distributions import Normal

from stable_baselines3.common.distributions import DiagGaussianDistribution
from stable_baselines3.common.policies import ActorCriticPolicy
from stable_baselines3.common.preprocessing import preprocess_obs
from stable_baselines3.common.torch_layers import CombinedExtractor
from stable_baselines3.common.type_aliases import PyTorchObs, Schedule


class MaskedDiagGaussianDistribution(DiagGaussianDistribution):
    """Diagonal Gaussian distribution that ignores padded action dimensions."""

    def __init__(self, action_dim: int):
        super().__init__(action_dim)
        self.current_mask: Optional[th.Tensor] = None

    def proba_distribution(  # type: ignore[override]
        self,
        mean_actions: th.Tensor,
        log_std: th.Tensor,
        action_mask: Optional[th.Tensor] = None,
    ) -> "MaskedDiagGaussianDistribution":
        if action_mask is None:
            action_mask = th.ones_like(mean_actions)
        self.current_mask = action_mask.float()
        action_std = th.ones_like(mean_actions) * log_std.exp()
        self.distribution = Normal(mean_actions, action_std)
        return self

    def log_prob(self, actions: th.Tensor) -> th.Tensor:
        log_prob = self.distribution.log_prob(actions)
        if self.current_mask is not None:
            log_prob = log_prob * self.current_mask
        return log_prob.sum(dim=1)

    def entropy(self) -> Optional[th.Tensor]:
        entropy = self.distribution.entropy()
        if self.current_mask is not None:
            entropy = entropy * self.current_mask
        return entropy.sum(dim=1)

    def sample(self) -> th.Tensor:
        actions = self.distribution.rsample()
        if self.current_mask is not None:
            actions = actions * self.current_mask
        return actions

    def mode(self) -> th.Tensor:
        actions = self.distribution.mean
        if self.current_mask is not None:
            actions = actions * self.current_mask
        return actions

    def actions_from_params(
        self,
        mean_actions: th.Tensor,
        log_std: th.Tensor,
        deterministic: bool = False,
        action_mask: Optional[th.Tensor] = None,
    ) -> th.Tensor:
        self.proba_distribution(mean_actions, log_std, action_mask=action_mask)
        return self.get_actions(deterministic=deterministic)

    def log_prob_from_params(
        self,
        mean_actions: th.Tensor,
        log_std: th.Tensor,
        action_mask: Optional[th.Tensor] = None,
    ) -> tuple[th.Tensor, th.Tensor]:
        actions = self.actions_from_params(mean_actions, log_std, action_mask=action_mask)
        return actions, self.log_prob(actions)


class MaskedActorCriticPolicy(ActorCriticPolicy):
    """Shared row-wise scorer with mask-aware critic pooling for PPO."""

    def __init__(
        self,
        observation_space: spaces.Space,
        action_space: spaces.Box,
        lr_schedule: Schedule,
        log_std_init: float = -2.0,
        **kwargs: Any,
    ) -> None:
        self.max_assets = int(action_space.shape[0])
        if not isinstance(observation_space, spaces.Dict):
            raise ValueError("MaskedActorCriticPolicy requires a Dict observation space.")
        feature_space = observation_space.spaces["features"]
        self.feature_count = int(feature_space.shape[-1])
        super().__init__(
            observation_space=observation_space,
            action_space=action_space,
            lr_schedule=lr_schedule,
            net_arch=[],
            activation_fn=nn.ReLU,
            ortho_init=True,
            features_extractor_class=CombinedExtractor,
            share_features_extractor=True,
            log_std_init=log_std_init,
            **kwargs,
        )

    @staticmethod
    def _init_linear(module: nn.Module, gain: float) -> None:
        if isinstance(module, nn.Linear):
            nn.init.orthogonal_(module.weight, gain=gain)
            nn.init.zeros_(module.bias)

    def _build(self, lr_schedule: Schedule) -> None:
        self.action_dist = MaskedDiagGaussianDistribution(self.max_assets)
        self.row_encoder = nn.Sequential(
            nn.Linear(self.feature_count, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
        )
        self.actor_head = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )
        self.value_net = nn.Sequential(
            nn.Linear(129, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
        )
        self.log_std = nn.Parameter(th.full((1,), self.log_std_init, dtype=th.float32))

        if self.ortho_init:
            self.row_encoder.apply(lambda module: self._init_linear(module, np.sqrt(2.0)))
            self.actor_head[0].apply(lambda module: self._init_linear(module, np.sqrt(2.0)))
            self.actor_head[2].apply(lambda module: self._init_linear(module, 0.01))
            self.value_net[0].apply(lambda module: self._init_linear(module, np.sqrt(2.0)))
            self.value_net[2].apply(lambda module: self._init_linear(module, 1.0))

        self.optimizer = self.optimizer_class(self.parameters(), lr=lr_schedule(1), **self.optimizer_kwargs)  # type: ignore[call-arg]

    def _preprocess_inputs(self, obs: PyTorchObs) -> tuple[th.Tensor, th.Tensor]:
        processed = preprocess_obs(obs, self.observation_space, normalize_images=self.normalize_images)
        if not isinstance(processed, dict):
            raise ValueError("Expected a dict observation after preprocessing.")
        features = processed["features"].float()
        mask = processed["mask"].float()
        if features.ndim == 2:
            features = features.unsqueeze(0)
        if mask.ndim == 1:
            mask = mask.unsqueeze(0)
        return features, mask

    def _encode_rows(self, obs: PyTorchObs) -> tuple[th.Tensor, th.Tensor]:
        features, mask = self._preprocess_inputs(obs)
        row_embeddings = self.row_encoder(features)
        return row_embeddings, mask

    def _actor_means(self, row_embeddings: th.Tensor, mask: th.Tensor) -> th.Tensor:
        means = self.actor_head(row_embeddings).squeeze(-1)
        return means * mask

    def _critic_values(self, row_embeddings: th.Tensor, mask: th.Tensor) -> th.Tensor:
        expanded_mask = mask.unsqueeze(-1)
        masked_embeddings = row_embeddings * expanded_mask
        active_counts = mask.sum(dim=1, keepdim=True).clamp(min=1.0)
        mean_pool = masked_embeddings.sum(dim=1) / active_counts

        inactive_fill = th.finfo(row_embeddings.dtype).min
        masked_for_max = row_embeddings.masked_fill(expanded_mask == 0.0, inactive_fill)
        max_pool = masked_for_max.max(dim=1).values
        has_active = (mask.sum(dim=1, keepdim=True) > 0.0).expand_as(max_pool)
        max_pool = th.where(has_active, max_pool, th.zeros_like(max_pool))

        normalized_count = active_counts / float(self.max_assets)
        critic_input = th.cat([mean_pool, max_pool, normalized_count], dim=1)
        return self.value_net(critic_input)

    def _distribution_from_obs(self, obs: PyTorchObs) -> tuple[MaskedDiagGaussianDistribution, th.Tensor]:
        row_embeddings, mask = self._encode_rows(obs)
        mean_actions = self._actor_means(row_embeddings, mask)
        distribution = self.action_dist.proba_distribution(mean_actions, self.log_std, action_mask=mask)
        values = self._critic_values(row_embeddings, mask)
        return distribution, values

    def forward(self, obs: PyTorchObs, deterministic: bool = False) -> tuple[th.Tensor, th.Tensor, th.Tensor]:
        distribution, values = self._distribution_from_obs(obs)
        actions = distribution.get_actions(deterministic=deterministic)
        log_prob = distribution.log_prob(actions)
        actions = actions.reshape((-1, *self.action_space.shape))
        return actions, values, log_prob

    def evaluate_actions(self, obs: PyTorchObs, actions: th.Tensor) -> tuple[th.Tensor, th.Tensor, Optional[th.Tensor]]:
        distribution, values = self._distribution_from_obs(obs)
        log_prob = distribution.log_prob(actions)
        entropy = distribution.entropy()
        return values, log_prob, entropy

    def get_distribution(self, obs: PyTorchObs) -> MaskedDiagGaussianDistribution:
        distribution, _ = self._distribution_from_obs(obs)
        return distribution

    def predict_values(self, obs: PyTorchObs) -> th.Tensor:
        _, values = self._distribution_from_obs(obs)
        return values
