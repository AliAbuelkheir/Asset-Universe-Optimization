from __future__ import annotations

from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2]
MODEL_ARTIFACTS_ROOT = APP_ROOT / "model-artifacts"
PPO_ARTIFACTS_ROOT = MODEL_ARTIFACTS_ROOT / "ranked-risk-model"
LEGACY_REPO_ROOT = Path(__file__).resolve().parents[3]


def artifact_root() -> Path:
    if PPO_ARTIFACTS_ROOT.exists():
        return APP_ROOT
    return LEGACY_REPO_ROOT
