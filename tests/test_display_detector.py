"""Tests for display auto-resolution detection (NSCB_AUTO_RES)."""

import json

import pytest

from nscb.display_detector import DisplayDetector

NIRI_DP4 = {
    "name": "DP-4",
    "current_mode": 1,
    "logical": {"x": 0, "y": 0, "width": 3440, "height": 1440},
    "modes": [
        {"width": 3440, "height": 1440, "refresh_rate": 59973},
        {"width": 3440, "height": 1440, "refresh_rate": 279962},
    ],
}

NIRI_HDMI2 = {
    "name": "HDMI-A-2",
    "current_mode": 0,
    "logical": {"x": 3440, "y": 0, "width": 2560, "height": 1440},
    "modes": [{"width": 2560, "height": 1440, "refresh_rate": 119998}],
}

KDE_OUT = {
    "outputs": [
        {
            "name": "DP-2",
            "enabled": True,
            "priority": 1,
            "currentModeId": "2",
            "modes": [
                {"id": "1", "size": {"width": 1920, "height": 1080}},
                {"id": "2", "size": {"width": 2560, "height": 1440}},
            ],
        }
    ]
}


@pytest.fixture
def niri_env(monkeypatch):
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "niri")
    monkeypatch.delenv("KDE_FULL_SESSION", raising=False)


@pytest.fixture
def kde_env(monkeypatch):
    monkeypatch.setenv("KDE_FULL_SESSION", "1")
    monkeypatch.delenv("XDG_CURRENT_DESKTOP", raising=False)


class TestBackendDetection:
    def test_niri_backend(self, niri_env, mocker):
        mocker.patch("nscb.display_detector.shutil.which", return_value="/usr/bin/niri")
        assert DisplayDetector.detect_backend() == "niri"

    def test_kde_backend(self, kde_env, mocker):
        mocker.patch(
            "nscb.display_detector.shutil.which", return_value="/usr/bin/kscreen-doctor"
        )
        assert DisplayDetector.detect_backend() == "kde"

    def test_no_backend(self, monkeypatch, mocker):
        monkeypatch.delenv("XDG_CURRENT_DESKTOP", raising=False)
        monkeypatch.delenv("KDE_FULL_SESSION", raising=False)
        mocker.patch("nscb.display_detector.shutil.which", return_value=None)
        assert DisplayDetector.detect_backend() == "none"


class TestNiriResolution:
    def test_primary_picks_top_left(self, niri_env, mocker):
        mocker.patch("nscb.display_detector.shutil.which", return_value="/usr/bin/niri")
        outputs = json.dumps([NIRI_HDMI2, NIRI_DP4])
        mocker.patch("subprocess.check_output", return_value=outputs)
        assert DisplayDetector.get_resolution() == (3440, 1440)

    def test_prefer_output(self, niri_env, mocker):
        mocker.patch("nscb.display_detector.shutil.which", return_value="/usr/bin/niri")
        mocker.patch(
            "subprocess.check_output", return_value=json.dumps([NIRI_DP4, NIRI_HDMI2])
        )
        assert DisplayDetector.get_resolution("HDMI-A-2") == (2560, 1440)

    def test_subprocess_failure_returns_none(self, niri_env, mocker):
        mocker.patch("nscb.display_detector.shutil.which", return_value="/usr/bin/niri")
        mocker.patch("subprocess.check_output", side_effect=FileNotFoundError)
        assert DisplayDetector.get_resolution() is None


class TestKdeResolution:
    def test_primary_by_priority(self, kde_env, mocker):
        mocker.patch(
            "nscb.display_detector.shutil.which", return_value="/usr/bin/kscreen-doctor"
        )
        mocker.patch("subprocess.check_output", return_value=json.dumps(KDE_OUT))
        assert DisplayDetector.get_resolution() == (2560, 1440)


class TestArgumentHelpers:
    def test_has_resolution_flag(self):
        assert DisplayDetector.has_resolution_flag(["-f", "-W", "1920"])
        assert DisplayDetector.has_resolution_flag(["-h", "1080"])
        assert DisplayDetector.has_resolution_flag(["--output-width=1920"])
        assert not DisplayDetector.has_resolution_flag(["-f", "--mangoapp"])

    def test_extract_prefer_output(self):
        assert DisplayDetector.extract_prefer_output(["-O", "DP-4", "-f"]) == "DP-4"
        assert (
            DisplayDetector.extract_prefer_output(["--prefer-output=HDMI-A-1"])
            == "HDMI-A-1"
        )
        assert DisplayDetector.extract_prefer_output(["-f"]) is None
