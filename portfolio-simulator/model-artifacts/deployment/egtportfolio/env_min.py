"""Minimal eval-only PortfolioEnv for inference.

This is a cut-down copy of src/env.py keeping only what's needed to produce
observations and convert action logits to portfolio weights. Training-side
reward computation, schedulers, and tier-specific reward coefficients are
not needed for inference.
"""

import gymnasium as gym
import numpy as np
from gymnasium import spaces


class PortfolioEnvMin(gym.Env):
    """Inference-only portfolio environment.

    Observation: (lookback, N_assets, F+1) — F features + 1 weight channel.
    Action:      raw logits → Dirichlet-mean projection → valid weights.

    No reward computation here; we only need step() to produce observations
    and to expose the weight-projection logic (`_masked_softmax`) so the
    package can post-process model logits identically to training.
    """

    metadata = {'render_modes': []}

    def __init__(
        self,
        feature_tensor: np.ndarray,
        active_matrix: np.ndarray,
        simple_returns: np.ndarray = None,
        max_weight: float = 0.25,
        min_weight: float = 0.0,
        dirichlet_prior: float = 0.5,
        lookback_window: int = 63,
    ):
        super().__init__()
        self.features = feature_tensor.astype(np.float32)
        self.active = active_matrix.astype(np.float32)
        # Returns are optional at inference (only needed if you want to
        # actually step through time and earn returns).
        if simple_returns is None:
            simple_returns = np.zeros((self.features.shape[0], self.features.shape[1]),
                                      dtype=np.float64)
        self.returns = simple_returns.astype(np.float64)

        self.n_dates, self.n_assets, self.n_features = feature_tensor.shape
        self.max_weight = max_weight
        self.min_weight = min_weight
        self.dirichlet_prior = dirichlet_prior
        self.lookback_window = lookback_window

        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf,
            shape=(self.lookback_window, self.n_assets, self.n_features + 1),
            dtype=np.float32,
        )
        self.action_space = spaces.Box(
            low=-10.0, high=10.0, shape=(self.n_assets,), dtype=np.float32
        )

        self.t = 0
        self.weights = np.zeros(self.n_assets, dtype=np.float64)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        # Start at the earliest valid position (need lookback days of history).
        self.t = max(self.lookback_window - 1, 60)
        active = self.active[self.t]
        n_active = active.sum()
        self.weights = (active / n_active).astype(np.float64) if n_active > 0 \
            else np.zeros(self.n_assets, dtype=np.float64)
        return self._get_obs(), {}

    def step(self, action):
        # Convert logits → valid weights
        active = self.active[self.t]
        new_weights = self._masked_softmax(action, active)

        next_t = self.t + 1
        # Compute portfolio return at the new step (using next-step returns).
        port_return = float(np.dot(new_weights, self.returns[next_t])) \
            if next_t < self.n_dates else 0.0

        self.weights = new_weights
        self.t = next_t

        terminated = self.t >= self.n_dates - 2
        info = {
            'portfolio_return': port_return,
            'turnover': float(np.sum(np.abs(new_weights - self.weights))),
            'weights': new_weights.copy(),
        }
        obs = self._get_obs() if not terminated else np.zeros(
            self.observation_space.shape, dtype=np.float32
        )
        return obs, 0.0, terminated, False, info

    def _get_obs(self) -> np.ndarray:
        """Build windowed observation: (lookback, N, F+1)."""
        start = self.t - self.lookback_window + 1
        if start < 0:
            pad_len = -start
            real = self.features[0:self.t + 1]
            padding = np.zeros(
                (pad_len, self.n_assets, self.n_features), dtype=np.float32
            )
            window = np.concatenate([padding, real], axis=0)
        else:
            window = self.features[start:self.t + 1]

        weights_channel = np.broadcast_to(
            self.weights.astype(np.float32)[np.newaxis, :, np.newaxis],
            (self.lookback_window, self.n_assets, 1),
        ).copy()
        return np.concatenate([window, weights_channel], axis=2).astype(np.float32)

    def _masked_softmax(self, logits: np.ndarray, active_mask: np.ndarray) -> np.ndarray:
        """Convert raw logits to valid portfolio weights via Dirichlet mean.

        Matches src/env.py:_masked_softmax exactly so inference produces
        weights identical to training/test scripts.
        """
        logits_arr = np.array(logits, dtype=np.float64).flatten()
        clipped = np.clip(logits_arr, -10.0, 10.0)
        alpha = np.log1p(np.exp(clipped)) + self.dirichlet_prior  # softplus + prior
        alpha = alpha * active_mask

        alpha_sum = alpha.sum()
        if alpha_sum > 1e-10:
            weights = alpha / alpha_sum
        else:
            n_active = active_mask.sum()
            if n_active > 0:
                weights = (active_mask / n_active).astype(np.float64)
            else:
                return np.zeros_like(alpha)

        # Min-weight floor (iterative redistribute)
        if self.min_weight is not None and self.min_weight > 0:
            for _ in range(10):
                below = (weights < self.min_weight) & (active_mask == 1)
                if not below.any():
                    break
                deficit = (self.min_weight - weights[below]).sum()
                weights[below] = self.min_weight
                above = (weights > self.min_weight) & (active_mask == 1)
                above_total = weights[above].sum()
                if above_total > 1e-10:
                    weights[above] -= deficit * (weights[above] / above_total)
            weights = np.maximum(weights, 0.0)

        # Max-weight cap (iterative redistribute)
        if self.max_weight is not None:
            for _ in range(10):
                over = weights > self.max_weight
                if not over.any():
                    break
                excess = (weights[over] - self.max_weight).sum()
                weights[over] = self.max_weight
                under = (weights < self.max_weight) & (weights > 0)
                under_total = weights[under].sum()
                if under_total > 1e-10:
                    weights[under] += excess * (weights[under] / under_total)
                elif under.sum() > 0:
                    weights[under] += excess / under.sum()

        weights = np.maximum(weights, 0.0)
        w_sum = weights.sum()
        if w_sum > 1e-10:
            weights /= w_sum
        return weights
