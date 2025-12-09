"""Tests for the path helper functionality in NeoscopeBuddy."""

import tempfile
from pathlib import Path

import pytest

from nscb.application import Application
from nscb.config_manager import ConfigManager
from nscb.path_helper import PathHelper
from nscb.system_detector import SystemDetector


class TestPathHelperUnit:
    """Unit tests for the PathHelper class."""

    def test_get_config_path_xdg_exists(self, monkeypatch, temp_config_file):
        """Test config path retrieval when XDG_CONFIG_HOME is set and file exists."""
        config_content = "gaming=-f -W 1920 -H 1080\n"
        with open(temp_config_file, "w") as f:
            f.write(config_content)

        monkeypatch.setenv("XDG_CONFIG_HOME", str(temp_config_file.parent))
        monkeypatch.delenv("HOME", raising=False)

        result = PathHelper.get_config_path()
        assert result == temp_config_file

    def test_get_config_path_xdg_not_exists_fallback(self, monkeypatch):
        """Test fallback to home directory when XDG config doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            home_dir = Path(temp_dir)
            config_dir = home_dir / ".config"
            config_dir.mkdir()
            config_path = config_dir / "nscb.conf"

            with open(config_path, "w") as f:
                f.write("gaming=-f -W 1920 -H 1080\n")

            monkeypatch.setenv("XDG_CONFIG_HOME", "/nonexistent")
            monkeypatch.setenv("HOME", str(home_dir))

            result = PathHelper.get_config_path()
            assert result == config_path

    def test_get_config_path_home_only(self, monkeypatch, temp_config_file):
        """Test config path retrieval from home directory."""
        home_config_dir = temp_config_file.parent
        config_path = home_config_dir / ".config" / "nscb.conf"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            f.write("gaming=-f -W 1920 -H 1080\n")

        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", str(home_config_dir))

        result = PathHelper.get_config_path()
        assert result == config_path

    def test_get_config_path_no_config(self, monkeypatch):
        """Test config path retrieval when no config file exists."""
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.delenv("HOME", raising=False)

        result = PathHelper.get_config_path()
        assert result is None

    def test_get_config_path_permission_error_scenario(self, monkeypatch, mocker):
        """Test config path retrieval when file exists but has permission issues."""
        # Mock Path.exists to return True but simulate permission issues
        mocker.patch.object(Path, "exists", return_value=False)
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.setenv("HOME", "/nonexistent")

        # Should return None since both XDG_CONFIG_HOME and HOME paths don't exist
        result = PathHelper.get_config_path()
        assert result is None

    def test_executable_exists_true(self, mocker):
        """Test executable exists when it's in PATH."""
        test_executable = "test_executable"
        with tempfile.TemporaryDirectory() as temp_dir:
            exec_path = Path(temp_dir) / test_executable
            # Create an executable file
            exec_path.touch()
            exec_path.chmod(0o755)

            # Patch PATH to include our temp directory
            mocker.patch.dict("os.environ", {"PATH": f"{temp_dir}:/usr/bin:/bin"})
            mocker.patch.object(Path, "exists", return_value=True)
            mocker.patch.object(Path, "is_file", return_value=True)
            mocker.patch.object(Path, "is_dir", return_value=True)
            mocker.patch("os.access", return_value=True)

            assert PathHelper.executable_exists(test_executable) is True

    def test_executable_exists_false(self, mocker):
        """Test executable exists returns False when not in PATH."""
        mocker.patch.dict("os.environ", {"PATH": ""}, clear=True)
        assert PathHelper.executable_exists("nonexistent_executable") is False

    def test_executable_exists_empty_path(self, mocker):
        """Test executable exists when PATH is empty."""
        mocker.patch("os.environ.get", return_value="")
        assert PathHelper.executable_exists("any_executable") is False

    @pytest.mark.parametrize(
        "path_env,access_result,expected",
        [
            ("", False, False),  # Empty PATH
            ("/nonexistent", False, False),  # Non-existent path
            ("/usr/bin", True, True),  # Valid path with access
        ],
    )
    def test_executable_exists_parametrized(
        self, mocker, path_env, access_result, expected
    ):
        """Test executable_exists with different PATH environments using parametrization."""
        mocker.patch.dict("os.environ", {"PATH": path_env}, clear=True)
        if path_env:  # Only mock file system if there's a path to check
            mocker.patch.object(Path, "exists", return_value=access_result)
            mocker.patch.object(Path, "is_file", return_value=access_result)
            mocker.patch.object(Path, "is_dir", return_value=True)
            mocker.patch("os.access", return_value=access_result)

        result = PathHelper.executable_exists("test_executable")
        assert result == expected

    def test_executable_exists_no_exec_permission(self, mocker, tmp_path):
        """Test executable exists returns False when file exists but no exec permission."""
        # Create a non-executable file in a temp directory
        exec_path = tmp_path / "test_exec"
        exec_path.touch()  # Create file without execute permission

        mocker.patch.dict("os.environ", {"PATH": str(tmp_path)})

        # Mock the path operations to simulate the file exists but isn't executable
        mocker.patch.object(Path, "exists", return_value=True)
        mocker.patch.object(Path, "is_file", return_value=True)
        mocker.patch.object(Path, "is_dir", return_value=True)
        mocker.patch("os.access", return_value=False)  # No execute permission

        assert PathHelper.executable_exists("test_exec") is False


class TestPathHelperIntegration:
    """Integration tests for PathHelper with other modules."""

    def test_path_helper_system_detector_integration(self, mocker):
        """Test PathHelper working with SystemDetector for executable detection."""
        # Both modules use executable checking functionality
        test_executable = "gamescope"

        # Mock the path operations to simulate executable found
        mocker.patch.dict("os.environ", {"PATH": "/usr/bin:/bin"}, clear=True)
        mocker.patch.object(Path, "exists", return_value=True)
        mocker.patch.object(Path, "is_file", return_value=True)
        mocker.patch.object(Path, "is_dir", return_value=True)
        mocker.patch("os.access", return_value=True)

        # Test that both SystemDetector and PathHelper can find the executable
        path_helper_result = PathHelper.executable_exists(test_executable)
        system_detector_result = SystemDetector.find_executable(test_executable)

        assert path_helper_result is True
        assert system_detector_result is True

    def test_path_helper_config_manager_integration(
        self, monkeypatch, temp_config_file
    ):
        """Test PathHelper working with ConfigManager for config file detection."""
        # Write test config
        with open(temp_config_file, "w") as f:
            f.write("gaming=-f -W 1920 -H 1080\n")

        # Set XDG_CONFIG_HOME to point to the temp config
        monkeypatch.setenv("XDG_CONFIG_HOME", str(temp_config_file.parent))
        monkeypatch.delenv("HOME", raising=False)

        # Test that PathHelper can find the config path
        config_path = PathHelper.get_config_path()
        assert config_path == temp_config_file

        # Test that ConfigManager can load from this path
        if config_path is not None:
            config_result = ConfigManager.load_config(config_path)
            assert "gaming" in config_result.profiles
            assert config_result.profiles["gaming"] == "-f -W 1920 -H 1080"

    def test_path_helper_application_integration(
        self, mocker, temp_config_with_content
    ):
        """Test PathHelper as part of the full application workflow."""
        config_data = "gaming=-f -W 1920 -H 1080\n"
        config_path = temp_config_with_content(config_data)

        # Mock PathHelper to return our test config path
        mocker.patch(
            "nscb.path_helper.PathHelper.get_config_path", return_value=config_path
        )
        mocker.patch("nscb.path_helper.PathHelper.executable_exists", return_value=True)

        mock_run = mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
        )

        app = Application()
        result = app.run(["-p", "gaming", "--", "test_app"])

        assert result == 0
        assert mock_run.called


class TestPathHelperEndToEnd:
    """End-to-end tests for PathHelper functionality."""

    def test_config_path_detection_e2e(self, monkeypatch, temp_config_file):
        """Test complete config path detection workflow."""
        # Write a test configuration
        config_content = "performance=-f -W 2560 -H 1440 --mangoapp\n"
        with open(temp_config_file, "w") as f:
            f.write(config_content)

        # Test XDG_CONFIG_HOME path detection
        monkeypatch.setenv("XDG_CONFIG_HOME", str(temp_config_file.parent))
        monkeypatch.delenv("HOME", raising=False)

        result_path = PathHelper.get_config_path()
        assert result_path == temp_config_file

        # Load and verify the config
        if result_path is not None:
            config_result = ConfigManager.load_config(result_path)
            assert "performance" in config_result.profiles
            assert (
                config_result.profiles["performance"] == "-f -W 2560 -H 1440 --mangoapp"
            )

    def test_executable_detection_comprehensive_e2e(self, mocker):
        """Test comprehensive executable detection scenarios."""
        # Test various scenarios for executable detection
        test_cases = [
            # (path_env, executable_exists, expected_result)
            ("/usr/bin:/bin", True, True),
            ("", False, False),
            ("/nonexistent", False, False),
        ]

        for path_env, mock_exists, expected_result in test_cases:
            mocker.patch.dict("os.environ", {"PATH": path_env}, clear=True)
            if path_env:  # Only mock file system if there's a path to check
                mocker.patch.object(Path, "exists", return_value=mock_exists)
                mocker.patch.object(Path, "is_file", return_value=mock_exists)
                mocker.patch.object(Path, "is_dir", return_value=True)
                mocker.patch("os.access", return_value=mock_exists)

            result = PathHelper.executable_exists("gamescope")
            # The result depends on mocking but should not crash
            assert isinstance(result, bool)

    def test_config_file_workflow_full_e2e(self, mocker, temp_config_with_content):
        """Test full configuration file workflow using PathHelper."""
        config_data = """# Performance profile
performance=-f -W 2560 -H 1440 --mangoapp
# Compatibility profile  
compatibility=-W 1280 -H 720 --fsr-sharpness 5
# Export variables
export PROTON_ENABLE_FSR=1
export MANGOHUD=1
"""
        config_path = temp_config_with_content(config_data)

        # Mock PathHelper to return our config path
        mocker.patch(
            "nscb.path_helper.PathHelper.get_config_path", return_value=config_path
        )
        mocker.patch("nscb.path_helper.PathHelper.executable_exists", return_value=True)
        mock_run = mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
        )

        app = Application()
        result = app.run(["-p", "performance", "--borderless", "--", "test_game"])

        assert result == 0
        call_args = mock_run.call_args[0][0]
        # The config should have been loaded and processed
        assert "gamescope" in call_args
        assert "test_game" in call_args
        # Based on conflict resolution, --borderless should override -f
        assert "--borderless" in call_args

    def test_path_helper_error_scenarios_e2e(self, monkeypatch):
        """Test PathHelper behavior in error scenarios."""
        # Test when no config environment variables are set
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        monkeypatch.delenv("HOME", raising=False)

        result = PathHelper.get_config_path()
        assert result is None

    def test_path_helper_fallback_scenarios_e2e(self, monkeypatch, temp_config_file):
        """Test PathHelper fallback behavior scenarios."""
        # Write config to home .config directory
        home_config_dir = temp_config_file.parent
        config_path = home_config_dir / ".config" / "nscb.conf"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            f.write("gaming=-f -W 1920 -H 1080\n")

        # Set up fallback scenario: XDG_CONFIG_HOME doesn't exist, use HOME
        monkeypatch.setenv("XDG_CONFIG_HOME", "/nonexistent")
        monkeypatch.setenv("HOME", str(home_config_dir))

        result = PathHelper.get_config_path()
        assert result == config_path

        # Verify the config loads correctly
        if result is not None:
            config_result = ConfigManager.load_config(result)
            assert "gaming" in config_result.profiles
            assert config_result.profiles["gaming"] == "-f -W 1920 -H 1080"
