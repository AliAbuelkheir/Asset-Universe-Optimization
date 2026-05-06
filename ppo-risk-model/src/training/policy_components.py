"""Reusable components for masked PPO policy construction."""

from __future__ import annotations

from typing import Optional, Sequence

import torch as th
from torch import nn
from torch.nn import functional as F
from torch.distributions import Normal

from stable_baselines3.common.distributions import DiagGaussianDistribution


class MaskedSigmoidGaussianDistribution(DiagGaussianDistribution):
    """Diagonal Gaussian distribution squashed to [0, 1] and masked on padded rows."""

    def __init__(self, action_dim: int, epsilon: float = 1e-6):
        super().__init__(action_dim)
        self.current_mask: Optional[th.Tensor] = None
        self.epsilon = float(epsilon)
        self.gaussian_actions: Optional[th.Tensor] = None

    def proba_distribution(  # type: ignore[override]
        self,
        mean_actions: th.Tensor,
        log_std: th.Tensor,
        action_mask: Optional[th.Tensor] = None,
    ) -> "MaskedSigmoidGaussianDistribution":
        if action_mask is None:
            action_mask = th.ones_like(mean_actions)
        self.current_mask = action_mask.float()
        action_std = th.ones_like(mean_actions) * log_std.exp()
        self.distribution = Normal(mean_actions, action_std)
        return self

    def _active_mask(self, reference: th.Tensor) -> th.Tensor:
        if self.current_mask is not None:
            return self.current_mask.to(reference.dtype)
        return th.ones_like(reference, dtype=reference.dtype)

    def entropy(self) -> None:
        return None

    def sample(self) -> th.Tensor:
        self.gaussian_actions = self.distribution.rsample()
        squashed_actions = th.sigmoid(self.gaussian_actions).clamp(self.epsilon, 1.0 - self.epsilon)
        return squashed_actions * self._active_mask(squashed_actions)

    def mode(self) -> th.Tensor:
        self.gaussian_actions = self.distribution.mean
        squashed_actions = th.sigmoid(self.gaussian_actions).clamp(self.epsilon, 1.0 - self.epsilon)
        return squashed_actions * self._active_mask(squashed_actions)

    def log_prob(self, actions: th.Tensor, gaussian_actions: Optional[th.Tensor] = None) -> th.Tensor:
        mask = self._active_mask(actions)
        if gaussian_actions is None:
            safe_actions = th.where(mask > 0.0, actions.clamp(self.epsilon, 1.0 - self.epsilon), th.full_like(actions, 0.5))
            gaussian_actions = th.logit(safe_actions, eps=self.epsilon)

        log_prob = self.distribution.log_prob(gaussian_actions)
        squash_correction = F.softplus(-gaussian_actions) + F.softplus(gaussian_actions)
        log_prob = (log_prob + squash_correction) * mask
        return log_prob.sum(dim=1)

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
        return actions, self.log_prob(actions, self.gaussian_actions)


def build_hidden_stack(input_dim: int, hidden_dims: Sequence[int]) -> tuple[nn.Sequential, int, list[nn.Linear]]:
    layers: list[nn.Module] = []
    linears: list[nn.Linear] = []
    current_dim = input_dim
    for hidden_dim in hidden_dims:
        linear = nn.Linear(current_dim, hidden_dim)
        linears.append(linear)
        layers.extend([linear, nn.ReLU()])
        current_dim = hidden_dim
    return nn.Sequential(*layers), current_dim, linears
