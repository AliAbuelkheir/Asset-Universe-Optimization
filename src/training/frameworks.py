"""Framework registry for the framework-first PPO study."""

from __future__ import annotations

from dataclasses import dataclass

from src import config


@dataclass(frozen=True)
class FrameworkSpec:
    framework_id: str
    lookback_months: int
    state_assembly_mode: str
    actor_context_mode: str
    observation_mode: str
    monthly_feature_dim: int
    input_dim: int
    row_encoder_dims: tuple[int, ...]
    actor_hidden_dims: tuple[int, ...]
    daily_strip_channels: int = 0
    daily_strip_length: int = 0
    uses_daily_strip: bool = False
    enabled: bool = True


FEATURE_DIM = len(config.MODEL_FEATURE_COLUMNS)


FRAMEWORK_REGISTRY: dict[str, FrameworkSpec] = {
    "pit_1m_shared_mlp": FrameworkSpec(
        framework_id="pit_1m_shared_mlp",
        lookback_months=1,
        state_assembly_mode="flat",
        actor_context_mode="none",
        observation_mode="flat_monthly",
        monthly_feature_dim=FEATURE_DIM,
        input_dim=FEATURE_DIM,
        row_encoder_dims=(64, 64),
        actor_hidden_dims=(32,),
    ),
    "pit_1m_context": FrameworkSpec(
        framework_id="pit_1m_context",
        lookback_months=1,
        state_assembly_mode="flat",
        actor_context_mode="pooled",
        observation_mode="flat_monthly",
        monthly_feature_dim=FEATURE_DIM,
        input_dim=FEATURE_DIM,
        row_encoder_dims=(64,),
        actor_hidden_dims=(64, 32),
    ),
    "pit_1m_dailystrip_shared_cnn": FrameworkSpec(
        framework_id="pit_1m_dailystrip_shared_cnn",
        lookback_months=1,
        state_assembly_mode="flat",
        actor_context_mode="none",
        observation_mode="monthly_plus_daily_strip",
        monthly_feature_dim=FEATURE_DIM,
        input_dim=FEATURE_DIM,
        row_encoder_dims=(64, 64),
        actor_hidden_dims=(32,),
        daily_strip_channels=config.DAILY_STRIP_CHANNELS,
        daily_strip_length=config.MAX_MONTHLY_OBS,
        uses_daily_strip=True,
    ),
    "pit_3m_flat_shared_mlp": FrameworkSpec(
        framework_id="pit_3m_flat_shared_mlp",
        lookback_months=3,
        state_assembly_mode="flat",
        actor_context_mode="none",
        observation_mode="flat_monthly",
        monthly_feature_dim=FEATURE_DIM * 3,
        input_dim=FEATURE_DIM * 3,
        row_encoder_dims=(64, 64),
        actor_hidden_dims=(32,),
    ),
    "pit_3m_flat_context": FrameworkSpec(
        framework_id="pit_3m_flat_context",
        lookback_months=3,
        state_assembly_mode="flat",
        actor_context_mode="pooled",
        observation_mode="flat_monthly",
        monthly_feature_dim=FEATURE_DIM * 3,
        input_dim=FEATURE_DIM * 3,
        row_encoder_dims=(64,),
        actor_hidden_dims=(64, 32),
    ),
    "pit_3m_flat_attention": FrameworkSpec(
        framework_id="pit_3m_flat_attention",
        lookback_months=3,
        state_assembly_mode="flat",
        actor_context_mode="attention",
        observation_mode="flat_monthly",
        monthly_feature_dim=FEATURE_DIM * 3,
        input_dim=FEATURE_DIM * 3,
        row_encoder_dims=(64,),
        actor_hidden_dims=(64, 32),
        enabled=False,
    ),
}


def get_framework_spec(framework_id: str) -> FrameworkSpec:
    try:
        framework = FRAMEWORK_REGISTRY[framework_id]
    except KeyError as exc:
        raise ValueError(f"Unknown framework_id: {framework_id}") from exc
    if not framework.enabled:
        raise ValueError(f"Framework {framework_id} is registered but not enabled in this phase.")
    return framework


def enabled_framework_ids() -> tuple[str, ...]:
    return tuple(spec.framework_id for spec in FRAMEWORK_REGISTRY.values() if spec.enabled)
