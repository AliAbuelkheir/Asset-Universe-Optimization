"""Custom masked PPO policies for the framework-first monthly ranking study."""

from __future__ import annotations

from typing import Any, Optional, Sequence

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


def _build_hidden_stack(input_dim: int, hidden_dims: Sequence[int]) -> tuple[nn.Sequential, int, list[nn.Linear]]:
    layers: list[nn.Module] = []
    linears: list[nn.Linear] = []
    current_dim = input_dim
    for hidden_dim in hidden_dims:
        linear = nn.Linear(current_dim, hidden_dim)
        linears.append(linear)
        layers.extend([linear, nn.ReLU()])
        current_dim = hidden_dim
    return nn.Sequential(*layers), current_dim, linears


class MaskedActorCriticPolicy(ActorCriticPolicy):
    """Shared row scorer with optional pooled context conditioning."""

    def __init__(
        self,
        observation_space: spaces.Space,
        action_space: spaces.Box,
        lr_schedule: Schedule,
        row_encoder_dims: Sequence[int] = (64, 64),
        actor_hidden_dims: Sequence[int] = (32,),
        actor_context_mode: str = "none",
        log_std_init: float = -2.0,
        **kwargs: Any,
    ) -> None:
        self.max_assets = int(action_space.shape[0])
        if not isinstance(observation_space, spaces.Dict):
            raise ValueError("MaskedActorCriticPolicy requires a Dict observation space.")
        if actor_context_mode == "attention":
            raise NotImplementedError("The attention framework is intentionally disabled in the active phase.")
        feature_space = observation_space.spaces["features"]
        self.feature_count = int(feature_space.shape[-1])
        self.uses_daily_strip = "daily_strip" in observation_space.spaces
        if self.uses_daily_strip:
            daily_space = observation_space.spaces["daily_strip"]
            self.daily_strip_length = int(daily_space.shape[1])
            self.daily_strip_channels = int(daily_space.shape[2])
        else:
            self.daily_strip_length = 0
            self.daily_strip_channels = 0
        self.row_encoder_dims = tuple(row_encoder_dims)
        self.actor_hidden_dims = tuple(actor_hidden_dims)
        self.actor_context_mode = actor_context_mode
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

    @staticmethod
    def _init_conv(module: nn.Module, gain: float) -> None:
        if isinstance(module, nn.Conv1d):
            nn.init.orthogonal_(module.weight, gain=gain)
            nn.init.zeros_(module.bias)

    def _build(self, lr_schedule: Schedule) -> None:
        self.action_dist = MaskedDiagGaussianDistribution(self.max_assets)

        self.row_encoder, self.row_dim, row_linears = _build_hidden_stack(self.feature_count, self.row_encoder_dims)
        self.daily_conv_layers: nn.Sequential | None = None
        self.daily_embedding_dim = 0
        if self.uses_daily_strip:
            self.daily_conv_layers = nn.Sequential(
                nn.Conv1d(self.daily_strip_channels, 16, kernel_size=3, padding=1),
                nn.ReLU(),
                nn.Conv1d(16, 32, kernel_size=3, padding=1),
                nn.ReLU(),
            )
            self.daily_embedding_dim = 32

        self.combined_row_dim = self.row_dim + self.daily_embedding_dim
        summary_dim = (self.combined_row_dim * 2) + 1
        actor_input_dim = self.combined_row_dim if self.actor_context_mode == "none" else self.combined_row_dim + summary_dim
        self.actor_hidden, actor_hidden_dim, actor_hidden_linears = _build_hidden_stack(actor_input_dim, self.actor_hidden_dims)
        self.actor_output = nn.Linear(actor_hidden_dim, 1)
        self.actor_activation = nn.Sigmoid()

        self.value_hidden, value_hidden_dim, value_hidden_linears = _build_hidden_stack(summary_dim, (64,))
        self.value_output = nn.Linear(value_hidden_dim, 1)
        self.log_std = nn.Parameter(th.full((1,), self.log_std_init, dtype=th.float32))

        if self.ortho_init:
            for linear in row_linears + actor_hidden_linears + value_hidden_linears:
                self._init_linear(linear, np.sqrt(2.0))
            if self.daily_conv_layers is not None:
                for module in self.daily_conv_layers:
                    self._init_conv(module, np.sqrt(2.0))
            self._init_linear(self.actor_output, 0.01)
            self._init_linear(self.value_output, 1.0)

        self.optimizer = self.optimizer_class(self.parameters(), lr=lr_schedule(1), **self.optimizer_kwargs)  # type: ignore[call-arg]

    def _preprocess_inputs(
        self,
        obs: PyTorchObs,
    ) -> tuple[th.Tensor, th.Tensor, th.Tensor | None, th.Tensor | None]:
        processed = preprocess_obs(obs, self.observation_space, normalize_images=self.normalize_images)
        if not isinstance(processed, dict):
            raise ValueError("Expected a dict observation after preprocessing.")
        features = processed["features"].float()
        mask = processed["mask"].float()
        if features.ndim == 2:
            features = features.unsqueeze(0)
        if mask.ndim == 1:
            mask = mask.unsqueeze(0)
        daily_strip = processed.get("daily_strip")
        daily_mask = processed.get("daily_mask")
        if daily_strip is not None:
            daily_strip = daily_strip.float()
            if daily_strip.ndim == 3:
                daily_strip = daily_strip.unsqueeze(0)
        if daily_mask is not None:
            daily_mask = daily_mask.float()
            if daily_mask.ndim == 2:
                daily_mask = daily_mask.unsqueeze(0)
        return features, mask, daily_strip, daily_mask

    def _encode_rows(self, obs: PyTorchObs) -> tuple[th.Tensor, th.Tensor]:
        features, mask, daily_strip, daily_mask = self._preprocess_inputs(obs)
        monthly_embeddings = self.row_encoder(features)
        if self.uses_daily_strip:
            if daily_strip is None or daily_mask is None or self.daily_conv_layers is None:
                raise ValueError("Daily-strip framework requires daily_strip and daily_mask observations.")
            batch_size, asset_count, day_count, channel_count = daily_strip.shape
            if day_count != self.daily_strip_length or channel_count != self.daily_strip_channels:
                raise ValueError("Observed daily strip tensor shape does not match the configured daily-strip encoder.")

            flat_strip = daily_strip.reshape(batch_size * asset_count, day_count, channel_count).permute(0, 2, 1)
            encoded = self.daily_conv_layers(flat_strip)
            flat_day_mask = daily_mask.reshape(batch_size * asset_count, day_count).unsqueeze(1)
            masked_encoded = encoded * flat_day_mask
            active_days = flat_day_mask.sum(dim=2).clamp(min=1.0)
            pooled_daily = masked_encoded.sum(dim=2) / active_days
            has_active_days = (flat_day_mask.sum(dim=2) > 0.0).expand_as(pooled_daily)
            pooled_daily = th.where(has_active_days, pooled_daily, th.zeros_like(pooled_daily))
            daily_embeddings = pooled_daily.view(batch_size, asset_count, self.daily_embedding_dim)
            row_embeddings = th.cat([monthly_embeddings, daily_embeddings], dim=2)
        else:
            row_embeddings = monthly_embeddings
        row_embeddings = row_embeddings * mask.unsqueeze(-1)
        return row_embeddings, mask

    def _pooled_summary(self, row_embeddings: th.Tensor, mask: th.Tensor) -> th.Tensor:
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
        return th.cat([mean_pool, max_pool, normalized_count], dim=1)

    def _actor_means(self, row_embeddings: th.Tensor, mask: th.Tensor) -> th.Tensor:
        if self.actor_context_mode == "pooled":
            summary = self._pooled_summary(row_embeddings, mask)
            expanded_summary = summary.unsqueeze(1).expand(-1, row_embeddings.shape[1], -1)
            actor_inputs = th.cat([row_embeddings, expanded_summary], dim=2)
        else:
            actor_inputs = row_embeddings

        hidden = self.actor_hidden(actor_inputs)
        means = self.actor_activation(self.actor_output(hidden)).squeeze(-1)
        return means * mask

    def _critic_values(self, row_embeddings: th.Tensor, mask: th.Tensor) -> th.Tensor:
        summary = self._pooled_summary(row_embeddings, mask)
        hidden = self.value_hidden(summary)
        return self.value_output(hidden)

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
