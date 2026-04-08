from __future__ import annotations

from pathlib import Path
import shutil
from uuid import uuid4

import _pytest.tmpdir as pytest_tmpdir
import pytest


_ORIGINAL_CLEANUP_DEAD_SYMLINKS = pytest_tmpdir.cleanup_dead_symlinks
_RUNTIME_ROOT = Path(__file__).resolve().parents[1] / ".test_runtime"


def _safe_cleanup_dead_symlinks(root: Path) -> None:
    try:
        _ORIGINAL_CLEANUP_DEAD_SYMLINKS(root)
    except PermissionError:
        # The current Windows workspace sandbox can block pytest's final
        # directory scan even after the tests themselves completed. Ignore that
        # cleanup-only failure so the real test result still surfaces.
        return


pytest_tmpdir.cleanup_dead_symlinks = _safe_cleanup_dead_symlinks


@pytest.fixture
def tmp_path() -> Path:
    _RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    temp_dir = _RUNTIME_ROOT / f"pytest_case_{uuid4().hex[:8]}"
    temp_dir.mkdir()
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
