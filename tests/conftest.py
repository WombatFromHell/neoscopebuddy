from pathlib import Path
from unittest.mock import patch

import pytest


class SystemExitCalled(Exception):
    """Custom exception to simulate sys.exit behavior in tests"""

    def __init__(self, code):
        self.code = code
        super().__init__(f"sys.exit({code}) called")


@pytest.fixture
def mock_system_exit():
    """Fixture to mock sys.exit for testing"""
    with patch(
        "sys.exit",
        side_effect=lambda code: (_ for _ in ()).throw(SystemExitCalled(code)),
    ) as mock:
        yield mock


@pytest.fixture
def mock_integration_setup():
    """Fixture to set up common mocking for integration tests"""
    with (
        patch("nscb.run_nonblocking", return_value=0) as mock_run_nonblocking,
        patch("nscb.build_command", side_effect=lambda x: "; ".join(x)) as mock_build,
        patch("builtins.print") as mock_print,
    ):
        yield {
            "run_nonblocking": mock_run_nonblocking,
            "build_command": mock_build,
            "print": mock_print,
        }
