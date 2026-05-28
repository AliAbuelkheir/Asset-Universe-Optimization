"""Custom masked PPO policies for the framework-first monthly ranking study."""

from __future__ import annotations

from typing import Any, Optional, Sequence

import numpy as np
import torch as th
from gymnasium import spaces
from torch import nn

from stable_baselines3.common.policies import ActorCriticPolicy
from stable_baselines3.common.preprocessing import preprocess_obs
from stable_baselines3.common.torch_layers import CombinedExtractor
from stable_baselines3.common.type_aliases import PyTorchObs, Schedule
from src.training.policy_components import MaskedSigmoidGaussianDistribution, build_hidden_stack


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
        daily_fusion_mode: str = "none",
        daily_path_scope: str = "none",
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
        self.daily_fusion_mode = daily_fusion_mode if self.uses_daily_strip else "none"
        if self.uses_daily_strip:
            # Older checkpoints did not persist a path scope. Those daily variants were all shared.
            self.daily_path_scope = "shared" if daily_path_scope == "none" else daily_path_scope
        else:
            self.daily_path_scope = "none"
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
        self.action_dist = MaskedSigmoidGaussianDistribution(self.max_assets)

        row_input_dim = self.feature_count
        self.daily_conv_layers: nn.Sequential | None = None
        self.daily_embedding_dim = 0
        self.actor_only_daily_flat_dim = 0
        if self.uses_daily_strip:
            if self.daily_path_scope not in {"shared", "actor_only"}:
                raise ValueError(f"Unsupported daily_path_scope: {self.daily_path_scope}")
            flat_daily_dim = (self.daily_strip_length * self.daily_strip_channels) + self.daily_strip_length
            if self.daily_fusion_mode == "flat_concat":
                if self.daily_path_scope == "shared":
                    row_input_dim += flat_daily_dim
                else:
                    self.actor_only_daily_flat_dim = flat_daily_dim
            elif self.daily_fusion_mode == "cnn_pool":
                self.daily_conv_layers = nn.Sequential(
                    nn.Conv1d(self.daily_strip_channels, 16, kernel_size=3, padding=1),
                    nn.ReLU(),
                    nn.Conv1d(16, 32, kernel_size=3, padding=1),
                    nn.ReLU(),
                )
                self.daily_embedding_dim = 32
            else:
                raise ValueError(f"Unsupported daily_fusion_mode: {self.daily_fusion_mode}")

        self.row_encoder, self.row_dim, row_linears = build_hidden_stack(row_input_dim, self.row_encoder_dims)

        self.critic_row_dim = self.row_dim
        if self.uses_daily_strip and self.daily_path_scope == "shared" and self.daily_fusion_mode == "cnn_pool":
            self.critic_row_dim += self.daily_embedding_dim

        self.actor_row_dim = self.critic_row_dim
        if self.uses_daily_strip and self.daily_path_scope == "actor_only":
            if self.daily_fusion_mode == "cnn_pool":
                self.actor_row_dim = self.row_dim + self.daily_embedding_dim
            else:
                self.actor_row_dim = self.row_dim + self.actor_only_daily_flat_dim

        summary_dim = (self.critic_row_dim * 2) + 1
        actor_input_dim = self.actor_row_dim if self.actor_context_mode == "none" else self.actor_row_dim + summary_dim
        self.actor_hidden, actor_hidden_dim, actor_hidden_linears = build_hidden_stack(actor_input_dim, self.actor_hidden_dims)
        self.actor_output = nn.Linear(actor_hidden_dim, 1)

        self.value_hidden, value_hidden_dim, value_hidden_linears = build_hidden_stack(summary_dim, (64,))
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

    def _flat_daily_inputs(self, masked_daily_strip: th.Tensor, daily_mask: th.Tensor) -> th.Tensor:
        batch_size, asset_count, day_count, channel_count = masked_daily_strip.shape
        flat_daily = masked_daily_strip.reshape(batch_size, asset_count, day_count * channel_count)
        return th.cat([flat_daily, daily_mask], dim=2)

    def _pooled_daily_embeddings(self, masked_daily_strip: th.Tensor, daily_mask: th.Tensor) -> th.Tensor:
        if self.daily_conv_layers is None:
            raise ValueError("CNN daily fusion requires initialized convolution layers.")
        batch_size, asset_count, day_count, channel_count = masked_daily_strip.shape
        flat_strip = masked_daily_strip.reshape(batch_size * asset_count, day_count, channel_count).permute(0, 2, 1)
        encoded = self.daily_conv_layers(flat_strip)
        flat_day_mask = daily_mask.reshape(batch_size * asset_count, day_count).unsqueeze(1)
        masked_encoded = encoded * flat_day_mask
        active_days = flat_day_mask.sum(dim=2).clamp(min=1.0)
        pooled_daily = masked_encoded.sum(dim=2) / active_days
        has_active_days = (flat_day_mask.sum(dim=2) > 0.0).expand_as(pooled_daily)
        pooled_daily = th.where(has_active_days, pooled_daily, th.zeros_like(pooled_daily))
        return pooled_daily.view(batch_size, asset_count, self.daily_embedding_dim)

    def _encode_rows(self, obs: PyTorchObs) -> tuple[th.Tensor, th.Tensor, th.Tensor]:
        features, mask, daily_strip, daily_mask = self._preprocess_inputs(obs)
        if self.uses_daily_strip:
            if daily_strip is None or daily_mask is None:
                raise ValueError("Daily-strip framework requires daily_strip and daily_mask observations.")
            batch_size, asset_count, day_count, channel_count = daily_strip.shape
            if day_count != self.daily_strip_length or channel_count != self.daily_strip_channels:
                raise ValueError("Observed daily strip tensor shape does not match the configured daily-strip encoder.")
            masked_daily_strip = daily_strip * daily_mask.unsqueeze(-1)

            if self.daily_fusion_mode == "flat_concat":
                flat_daily_inputs = self._flat_daily_inputs(masked_daily_strip, daily_mask)
                if self.daily_path_scope == "shared":
                    row_inputs = th.cat([features, flat_daily_inputs], dim=2)
                    row_embeddings = self.row_encoder(row_inputs)
                    actor_row_embeddings = row_embeddings
                    critic_row_embeddings = row_embeddings
                else:
                    monthly_embeddings = self.row_encoder(features)
                    actor_row_embeddings = th.cat([monthly_embeddings, flat_daily_inputs], dim=2)
                    critic_row_embeddings = monthly_embeddings
            else:
                monthly_embeddings = self.row_encoder(features)
                daily_embeddings = self._pooled_daily_embeddings(masked_daily_strip, daily_mask)
                if self.daily_path_scope == "shared":
                    row_embeddings = th.cat([monthly_embeddings, daily_embeddings], dim=2)
                    actor_row_embeddings = row_embeddings
                    critic_row_embeddings = row_embeddings
                else:
                    actor_row_embeddings = th.cat([monthly_embeddings, daily_embeddings], dim=2)
                    critic_row_embeddings = monthly_embeddings
        else:
            monthly_embeddings = self.row_encoder(features)
            actor_row_embeddings = monthly_embeddings
            critic_row_embeddings = monthly_embeddings
        actor_row_embeddings = actor_row_embeddings * mask.unsqueeze(-1)
        critic_row_embeddings = critic_row_embeddings * mask.unsqueeze(-1)
        return actor_row_embeddings, critic_row_embeddings, mask

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

    def _actor_means(self, actor_row_embeddings: th.Tensor, mask: th.Tensor, summary: th.Tensor) -> th.Tensor:
        if self.actor_context_mode == "pooled":
            expanded_summary = summary.unsqueeze(1).expand(-1, actor_row_embeddings.shape[1], -1)
            actor_inputs = th.cat([actor_row_embeddings, expanded_summary], dim=2)
        else:
            actor_inputs = actor_row_embeddings

        hidden = self.actor_hidden(actor_inputs)
        means = self.actor_output(hidden).squeeze(-1)
        return means * mask

    def _critic_values(self, summary: th.Tensor) -> th.Tensor:
        hidden = self.value_hidden(summary)
        return self.value_output(hidden)

    def _distribution_from_obs(self, obs: PyTorchObs) -> tuple[MaskedSigmoidGaussianDistribution, th.Tensor]:
        actor_row_embeddings, critic_row_embeddings, mask = self._encode_rows(obs)
        summary = self._pooled_summary(critic_row_embeddings, mask)
        mean_actions = self._actor_means(actor_row_embeddings, mask, summary)
        distribution = self.action_dist.proba_distribution(mean_actions, self.log_std, action_mask=mask)
        values = self._critic_values(summary)
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

    def get_distribution(self, obs: PyTorchObs) -> MaskedSigmoidGaussianDistribution:
        distribution, _ = self._distribution_from_obs(obs)
        return distribution

    def predict_values(self, obs: PyTorchObs) -> th.Tensor:
        _, values = self._distribution_from_obs(obs)
        return values
