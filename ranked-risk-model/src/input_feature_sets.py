"""Registry for canonical and shadow input feature sets."""

from __future__ import annotations

from dataclasses import dataclass

from src import config


@dataclass(frozen=True)
class InputFeatureSet:
    input_feature_set_id: str
    description: str
    feature_columns: tuple[str, ...]


CANONICAL_INPUT_FEATURE_SET = InputFeatureSet(
    input_feature_set_id=config.DEFAULT_INPUT_FEATURE_SET_ID,
    description="Canonical 11-feature monthly input set.",
    feature_columns=tuple(config.MODEL_FEATURE_COLUMNS),
)


def additive_candidate_input_feature_set(candidate_id: str) -> InputFeatureSet:
    return InputFeatureSet(
        input_feature_set_id=f"shadow_add_{candidate_id}",
        description=f"Canonical 11-feature set plus additive shadow candidate `{candidate_id}`.",
        feature_columns=tuple(config.MODEL_FEATURE_COLUMNS) + (candidate_id,),
    )


INPUT_FEATURE_SET_REGISTRY: dict[str, InputFeatureSet] = {
    CANONICAL_INPUT_FEATURE_SET.input_feature_set_id: CANONICAL_INPUT_FEATURE_SET,
}


def register_input_feature_set(input_feature_set: InputFeatureSet) -> None:
    INPUT_FEATURE_SET_REGISTRY[input_feature_set.input_feature_set_id] = input_feature_set


def get_input_feature_set(input_feature_set_id: str) -> InputFeatureSet:
    if input_feature_set_id not in INPUT_FEATURE_SET_REGISTRY and input_feature_set_id.startswith("shadow_add_"):
        candidate_id = input_feature_set_id.removeprefix("shadow_add_")
        register_input_feature_set(additive_candidate_input_feature_set(candidate_id))
    try:
        return INPUT_FEATURE_SET_REGISTRY[input_feature_set_id]
    except KeyError as exc:
        raise ValueError(f"Unknown input_feature_set_id: {input_feature_set_id}") from exc


def input_feature_set_ids() -> tuple[str, ...]:
    return tuple(INPUT_FEATURE_SET_REGISTRY)
