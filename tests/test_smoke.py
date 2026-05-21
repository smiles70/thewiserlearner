"""Smoke tests that prove the repo is well-formed.

These tests run on every push and PR via .github/workflows/ci.yml.
They check repo-level invariants, not pipeline behaviour. Pipeline tests will
arrive in Part 5 alongside the pipeline modules they exercise.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_readme_exists() -> None:
    assert (REPO_ROOT / "README.md").is_file()


def test_license_is_busl() -> None:
    license_text = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "Business Source License 1.1" in license_text
    assert "Change Date:" in license_text


def test_required_top_level_dirs_exist() -> None:
    for name in (
        "library",
        "contract",
        "skills",
        "pipeline",
        "mcp",
        "episodes",
        "analytics",
        "docs",
        "tests",
    ):
        assert (REPO_ROOT / name).is_dir(), f"missing directory: {name}"


def test_library_index_exists() -> None:
    assert (REPO_ROOT / "library" / "INDEX.md").is_file()


def test_no_committed_secrets_env() -> None:
    # A committed .env would be an immediate security issue.
    assert not (REPO_ROOT / ".env").exists()


def test_pyproject_declares_python_311_plus() -> None:
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'requires-python = ">=3.11"' in text
