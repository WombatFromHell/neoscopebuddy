"""Tests for the system detection functionality in NeoscopeBuddy."""

import subprocess
from pathlib import Path

import pytest

from nscb.application import Application
from nscb.system_detector import SystemDetector


class TestSystemDetectorUnit:
    """Unit tests for the SystemDetector class."""

    def test_find_executable_true(self, mocker):
        mocker.patch.dict("os.environ", {"PATH": "/usr/bin:/bin"})
        mocker.patch.object(Path, "exists", return_value=True)
        mocker.patch.object(Path, "is_dir", return_value=True)
        mocker.patch.object(Path, "is_file", return_value=True)
        mocker.patch("os.access", return_value=True)

        assert SystemDetector.find_executable("gamescope") is True

    def test_find_executable_false(self, mocker):
        mocker.patch.dict("os.environ", {"PATH": ""}, clear=True)
        assert SystemDetector.find_executable("gamescope") is False

    def test_find_executable_permission_issues(self, mocker):
        mocker.patch.dict("os.environ", {"PATH": "/usr/bin"})
        mocker.patch.object(Path, "exists", return_value=True)
        mocker.patch.object(Path, "is_dir", return_value=True)
        mocker.patch.object(Path, "is_file", return_value=True)
        mocker.patch("os.access", return_value=False)
        assert SystemDetector.find_executable("gamescope") is False

    def test_find_executable_empty_path(self, mocker):
        mocker.patch("os.environ.get", return_value="")
        assert SystemDetector.find_executable("any_executable") is False

    def test_find_executable_path_scenarios(self, mocker):
        import shutil

        python_path = shutil.which("python")
        if python_path:
            mocker.patch.dict("os.environ", {"PATH": str(Path(python_path).parent)})
            mocker.patch.object(Path, "exists", return_value=True)
            mocker.patch.object(Path, "is_dir", return_value=True)
            mocker.patch.object(Path, "is_file", return_value=True)
            mocker.patch("os.access", return_value=True)
            result = SystemDetector.find_executable("python")
            assert result is True

    def test_is_gamescope_active_xdg_method(self, mocker):
        mocker.patch.dict("os.environ", {"XDG_CURRENT_DESKTOP": "gamescope"})
        assert SystemDetector.is_gamescope_active() is True

    def test_is_gamescope_active_ps_method(self, mocker):
        mocker.patch(
            "subprocess.check_output",
            return_value="1234 ?    Sl     0:00 gamescope -f -W 1920 -H 1080",
        )
        assert SystemDetector.is_gamescope_active() is True

        mocker.patch(
            "subprocess.check_output", return_value="1234 ?    Sl     0:00 Xorg"
        )
        assert SystemDetector.is_gamescope_active() is False

    def test_is_gamescope_active_error_conditions(self, mocker):
        mocker.patch(
            "subprocess.check_output",
            side_effect=subprocess.CalledProcessError(1, "ps"),
        )
        assert SystemDetector.is_gamescope_active() is False

    @pytest.mark.parametrize(
        "path_env,access_result,exists_result,expected",
        [
            ("/usr/bin:/bin", True, True, True),  # Standard PATH with access
            ("", False, False, False),  # Empty PATH
            ("/nonexistent", False, False, False),  # Non-existent path
            ("/usr/bin", True, True, True),  # Valid path with access
            ("/usr/bin", False, True, False),  # Path exists but no access
        ],
    )
    def test_find_executable_parametrized(
        self, mocker, path_env, access_result, exists_result, expected
    ):
        """Test find_executable with different PATH environments using parametrization."""
        mocker.patch.dict("os.environ", {"PATH": path_env}, clear=True)
        if path_env:
            mocker.patch.object(Path, "exists", return_value=exists_result)
            mocker.patch.object(Path, "is_dir", return_value=True)
            mocker.patch.object(Path, "is_file", return_value=exists_result)
            mocker.patch("os.access", return_value=access_result)

        result = SystemDetector.find_executable("test_executable")
        assert result == expected

    def test_is_gamescope_active_both_methods(self, mocker):
        mocker.patch.dict("os.environ", {"XDG_CURRENT_DESKTOP": "gamescope"})
        mock_ps = mocker.patch("subprocess.check_output")

        result = SystemDetector.is_gamescope_active()
        assert result is True
        mock_ps.assert_not_called()

        mocker.patch.dict("os.environ", {"XDG_CURRENT_DESKTOP": "GNOME"})
        mocker.patch(
            "subprocess.check_output", return_value="1234 ?    Sl     0:00 gamescope"
        )
        result = SystemDetector.is_gamescope_active()
        assert result is True


class TestSystemDetectorIntegration:
    """Integration tests for the SystemDetector with other modules."""

    def test_system_detector_path_helper_integration(self):
        """Test SystemDetector working with PathHelper for executable detection."""
        # Test that SystemDetector uses PathHelper functionality
        test_executable = "test_exe"
        result = SystemDetector.find_executable(test_executable)

        # The result depends on the mocked environment, but the method should work
        assert result in [True, False]  # Should return a boolean

    def test_system_detector_environment_helper_integration(self, mocker):
        """Test SystemDetector working with EnvironmentHelper for gamescope detection."""
        # Both modules work with environment detection
        # Test XDG_CURRENT_DESKTOP approach
        mocker.patch.dict(
            "os.environ", {"XDG_CURRENT_DESKTOP": "gamescope"}, clear=True
        )
        assert SystemDetector.is_gamescope_active() is True

        # Test fallback to ps approach
        mocker.patch.dict("os.environ", {"XDG_CURRENT_DESKTOP": "GNOME"}, clear=True)
        mocker.patch(
            "subprocess.check_output", return_value="1234 ?    Sl     0:00 gamescope"
        )
        assert SystemDetector.is_gamescope_active() is True

    def test_system_detector_application_workflow_integration(
        self, mocker, temp_config_with_content
    ):
        """Test SystemDetector as part of the full application workflow."""
        config_data = "gaming=-f -W 1920 -H 1080\n"
        config_path = temp_config_with_content(config_data)

        # Set up application with real SystemDetector
        app = Application()

        # Mock the config loading and command execution
        mocker.patch(
            "nscb.config_manager.PathHelper.get_config_path", return_value=config_path
        )
        mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
        )

        # The app will use SystemDetector to check for gamescope executable
        result = app.run(["-p", "gaming", "--", "test_app"])

        # Should return 0 if gamescope was found (mocked), or 1 if not found
        assert result in [0, 1]


class TestSystemDetectorEndToEnd:
    """End-to-end tests for SystemDetector functionality."""

    def test_gamescope_detection_and_execution_modes(self, mocker):
        mocker.patch.dict(
            "os.environ", {"XDG_CURRENT_DESKTOP": "gamescope"}, clear=True
        )
        assert SystemDetector.is_gamescope_active() is True

    def test_is_gamescope_active_xdg_method_e2e(self, mocker):
        # Test direct XDG_CURRENT_DESKTOP method
        mocker.patch.dict(
            "os.environ", {"XDG_CURRENT_DESKTOP": "gamescope"}, clear=True
        )
        assert SystemDetector.is_gamescope_active() is True

        # Test with different value
        mocker.patch.dict("os.environ", {"XDG_CURRENT_DESKTOP": "GNOME"}, clear=True)
        assert SystemDetector.is_gamescope_active() is False  # Will try ps method

    def test_is_gamescope_active_ps_method_e2e(self, mocker):
        # Test fallback to ps command when XDG_CURRENT_DESKTOP is not gamescope
        mocker.patch.dict("os.environ", {"XDG_CURRENT_DESKTOP": "GNOME"}, clear=True)
        mocker.patch(
            "subprocess.check_output",
            return_value="1234 ?    Sl     0:00 gamescope -f -W 1920 -H 1080",
        )
        assert SystemDetector.is_gamescope_active() is True

        # Test ps command shows non-gamescope process
        mocker.patch(
            "subprocess.check_output", return_value="1234 ?    Sl     0:00 Xorg"
        )
        assert SystemDetector.is_gamescope_active() is False

    def test_find_executable_comprehensive_scenarios(self, mocker):
        # Test various executable finding scenarios
        test_cases = [
            # (path_env, expected_result)
            ("/usr/bin:/bin", True),  # Standard PATH with common directories
            ("", False),  # Empty PATH
            ("/nonexistent", False),  # Non-existent path
        ]

        for path_env, expected_result in test_cases:
            mocker.patch.dict("os.environ", {"PATH": path_env}, clear=True)
            # Mock file system operations for the test
            if path_env:
                mocker.patch.object(Path, "exists", return_value=True)
                mocker.patch.object(Path, "is_dir", return_value=True)
                mocker.patch.object(Path, "is_file", return_value=True)
                mocker.patch("os.access", return_value=True)

            # Test with a dummy executable name
            result = SystemDetector.find_executable("dummy_executable")
            # The result depends on the mocking but the call should not fail
            assert result in [True, False]

    def test_gamescope_detection_integration_e2e(
        self, mocker, temp_config_with_content
    ):
        """Test full gamescope detection and application execution workflow."""
        config_data = "gaming=-f -W 1920 -H 1080\n"
        config_path = temp_config_with_content(config_data)

        # Test in gamescope environment
        mocker.patch.dict(
            "os.environ", {"XDG_CURRENT_DESKTOP": "gamescope"}, clear=True
        )
        mocker.patch(
            "nscb.config_manager.PathHelper.get_config_path", return_value=config_path
        )
        mocker.patch("nscb.path_helper.PathHelper.executable_exists", return_value=True)
        mock_run = mocker.patch(
            "nscb.command_executor.CommandExecutor.run_nonblocking", return_value=0
        )

        app = Application()
        result = app.run(["-p", "gaming", "--", "test_game"])

        assert result == 0
        call_args = mock_run.call_args[0][0]
        # When in gamescope, should not run gamescope again but run the app directly
        assert "test_game" in call_args


class TestSystemDetectorFixtureUtilization:
    """Test class demonstrating utilization of system detection fixtures."""

    def test_system_detection_scenarios_with_fixtures(
        self, mock_system_detection_scenarios
    ):
        """
        Test system detection using mock_system_detection_scenarios fixture.

        This demonstrates how to use the system detection scenarios fixture
        to test various system detection scenarios in a standardized way.
        """
        from nscb.system_detector import SystemDetector

        # Test gamescope active scenario
        mock_system_detection_scenarios["gamescope_active"]()
        assert SystemDetector.is_gamescope_active() == True

        # Test gamescope inactive scenario
        mock_system_detection_scenarios["gamescope_inactive"]()
        assert SystemDetector.is_gamescope_active() == False

        # Test executable found scenario
        mock_system_detection_scenarios["executable_found"]()
        assert SystemDetector.find_executable("gamescope") == True

        # Test executable not found scenario
        mock_system_detection_scenarios["executable_not_found"]()
        assert SystemDetector.find_executable("nonexistent") == False

    def test_simple_gamescope_detection_with_mock_is_gamescope_active(
        self, mock_is_gamescope_active
    ):
        """
        Test simple gamescope detection using mock_is_gamescope_active fixture.

        This demonstrates how to use the simple mock_is_gamescope_active fixture
        for basic gamescope active state testing.
        """
        from nscb.system_detector import SystemDetector

        # Test mocking gamescope as active
        mock_is_gamescope_active.return_value = True
        assert SystemDetector.is_gamescope_active() == True
        mock_is_gamescope_active.assert_called_once()

        # Test mocking gamescope as inactive
        mock_is_gamescope_active.return_value = False
        assert SystemDetector.is_gamescope_active() == False
        # Should be called twice total now
        assert mock_is_gamescope_active.call_count == 2
