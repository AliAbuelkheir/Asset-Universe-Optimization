"""Set-based (permutation-invariant) feature extractor for portfolio RL.

Output:
  features_dim = 256 (the mean-pooled vector used by SB3's contract)

Also stashes `per_asset_features` on the module after each forward pass —
shape (batch, N, hidden_dim) — for the policy head to consume per-asset.

The architecture is N-invariant: Conv1D weights are shared across assets,
the mean-pool over assets is order-agnostic, and the final Linear projection
operates on the pooled vector (not on a per-asset concatenation).
"""

import gymnasium as gym
import torch
import torch.nn as nn

from stable_baselines3.common.torch_layers import BaseFeaturesExtractor


class SetBasedFeatureExtractor(BaseFeaturesExtractor):
    """Per-asset Conv1D + mean-pool over assets.

    Args:
        observation_space: Box with shape (lookback, n_assets, n_channels).
            Note: n_assets can be ANY value at inference time.
        features_dim: dim of the mean-pooled output (256 by default).
        hidden_dim: per-asset hidden dim before pooling (64 by default).
    """

    def __init__(self, observation_space: gym.spaces.Box,
                 features_dim: int = 256, hidden_dim: int = 64):
        super().__init__(observation_space, features_dim)
        self.lookback = observation_space.shape[0]
        self.n_channels = observation_space.shape[2]  # 23 = 22 features + 1 weight
        self.hidden_dim = hidden_dim

        self.conv = nn.Sequential(
            nn.Conv1d(self.n_channels, 32, kernel_size=5, padding=2),
            nn.ReLU(),
            nn.Conv1d(32, hidden_dim, kernel_size=5, padding=2),
            nn.ReLU(),
            nn.AdaptiveAvgPool1d(1),
        )
        self.proj = nn.Sequential(
            nn.Linear(hidden_dim, features_dim),
            nn.ReLU(),
        )

        # Stash for the policy to fetch per-asset features after forward()
        self._per_asset_cache: torch.Tensor | None = None

    def forward(self, observations: torch.Tensor) -> torch.Tensor:
        b, T, n, c = observations.shape

        # (b, T, n, c) -> (b, n, c, T) -> (b*n, c, T)
        x = observations.permute(0, 2, 3, 1).reshape(b * n, c, T)
        x = self.conv(x).squeeze(-1)              # (b*n, hidden_dim)
        per_asset = x.reshape(b, n, self.hidden_dim)  # (b, n, hidden_dim)

        # Stash for the policy to use per-asset features
        self._per_asset_cache = per_asset

        # Mean-pool over assets, then project
        pooled = per_asset.mean(dim=1)            # (b, hidden_dim)
        return self.proj(pooled)                   # (b, features_dim)
