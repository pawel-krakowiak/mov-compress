"""Tests for loading and saving persistent settings."""

import json

import pytest

from mov_compress import config
from mov_compress.config import DEFAULT_TARGET_MB, Settings


@pytest.fixture(autouse=True)
def config_path(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    monkeypatch.setattr(config, "config_file", lambda: path)
    return path


def test_defaults_apply_when_no_file_exists():
    settings = Settings.load()
    assert settings.target_mb == DEFAULT_TARGET_MB
    assert settings.output_dir == ""


def test_settings_survive_a_round_trip(config_path):
    Settings(target_mb=12.5, output_dir="/out", browse_dir="/in").save()
    assert Settings.load() == Settings(target_mb=12.5, output_dir="/out", browse_dir="/in")


def test_unknown_keys_are_ignored(config_path):
    config_path.write_text(json.dumps({"target_mb": 8.0, "surprise": True}))
    assert Settings.load().target_mb == 8.0


@pytest.mark.parametrize("content", ["not json", "[]", '"a string"', "null"])
def test_a_broken_file_falls_back_to_defaults(config_path, content):
    config_path.write_text(content)
    assert Settings.load() == Settings()


def test_saving_creates_the_config_directory(tmp_path, monkeypatch):
    nested = tmp_path / "deep" / "nested" / "config.json"
    monkeypatch.setattr(config, "config_file", lambda: nested)
    Settings(target_mb=5.0).save()
    assert json.loads(nested.read_text())["target_mb"] == 5.0
