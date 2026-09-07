"""Unit tests for src/extract.py's config.yml loading (load_extract_config).

Covers the reproducibility requirement that every script runs with sane
defaults if config.yml is absent, and that values it does set override
the defaults correctly.
"""
from pathlib import Path

import extract


def test_load_extract_config_falls_back_to_defaults_when_file_missing(tmp_path):
    """A nonexistent config path should yield exactly the built-in
    defaults, not raise."""
    missing_path = tmp_path / "does_not_exist.yml"

    result = extract.load_extract_config(config_path=missing_path)

    assert result == extract._EXTRACT_CONFIG_DEFAULTS


def test_load_extract_config_overrides_only_the_keys_it_sets(tmp_path):
    """Values present in config.yml's `extract:` section should override
    the corresponding default; unset keys should keep their default."""
    config_file = tmp_path / "config.yml"
    config_file.write_text("extract:\n  max_pages: 20\n  repo_owner: octocat\n")

    result = extract.load_extract_config(config_path=config_file)

    assert result["max_pages"] == 20
    assert result["repo_owner"] == "octocat"
    # Untouched keys still fall back to the defaults.
    assert result["per_page"] == extract._EXTRACT_CONFIG_DEFAULTS["per_page"]


def test_load_extract_config_handles_empty_file(tmp_path):
    """An empty config.yml (yaml.safe_load returns None) should not crash
    and should yield pure defaults."""
    config_file = tmp_path / "config.yml"
    config_file.write_text("")

    result = extract.load_extract_config(config_path=config_file)

    assert result == extract._EXTRACT_CONFIG_DEFAULTS


def test_repo_root_config_yml_is_used_by_default():
    """extract.CONFIG_PATH should point at the real repo-root config.yml,
    and the module-level constants derived from it should match its
    current on-disk values (guards against the two drifting apart)."""
    assert extract.CONFIG_PATH == Path(__file__).resolve().parent.parent / "config.yml"
    assert extract.CONFIG_PATH.exists()
