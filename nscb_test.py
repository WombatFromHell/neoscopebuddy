#!/usr/bin/python3
import unittest
from unittest.mock import patch
import os
import sys
import tempfile
from pathlib import Path
from io import StringIO

# Add the parent directory to the path so we can import nscb
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import nscb  # This should be the name of your script without .py extension

class TestNSCB(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

    def test_find_config_file_xdg(self):
        """Test finding config file in XDG_CONFIG_HOME."""
        xdg_config_home = os.path.join(self.temp_dir.name, 'xdg_config')
        os.makedirs(xdg_config_home)
        config_path = os.path.join(xdg_config_home, 'nscb.conf')

        with open(config_path, 'w') as f:
            f.write('test=value')

        with patch.dict(os.environ, {'XDG_CONFIG_HOME': xdg_config_home}):
            result = nscb.find_config_file()
            self.assertEqual(result, Path(config_path))

    @patch('nscb.find_executable')
    @patch('sys.argv', ['nscb.py', '--profile', 'test', 'app', 'arg1'])
    def test_main_success(self, mock_find_executable):
        """Test main function success path."""
        mock_find_executable.return_value = True

        config_content = 'test=--some-flag'
        config_path = os.path.join(self.temp_dir.name, 'nscb.conf')
        with open(config_path, 'w') as f:
            f.write(config_content)

        with patch.dict(os.environ, {'XDG_CONFIG_HOME': self.temp_dir.name}):
            with patch('builtins.print') as _:
                with patch('os.execvp') as mock_execvp:
                    nscb.main()
                    # Check that execvp was called with the right arguments
                    mock_execvp.assert_called_once_with(
                        'gamescope',
                        ['gamescope', '--some-flag', '--', 'app', 'arg1']
                    )

    @patch('nscb.find_executable')
    def test_main_no_gamescope(self, mock_find_executable):
        """Test main function when gamescope is not found."""
        mock_find_executable.return_value = False

        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            with self.assertRaises(SystemExit) as cm:
                nscb.main()
            self.assertEqual(cm.exception.code, 1)
            self.assertIn("Error: gamescope not found in PATH or is not executable", mock_stderr.getvalue())

    def test_main_invalid_profile(self):
        """Test main function with invalid profile."""
        config_content = 'profile1=arg1'
        config_path = os.path.join(self.temp_dir.name, 'nscb.conf')
        with open(config_path, 'w') as f:
            f.write(config_content)

        with patch.dict(os.environ, {'XDG_CONFIG_HOME': self.temp_dir.name}):
            with patch('sys.argv', ['nscb.py', '--profile', 'invalid']):
                with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
                    with self.assertRaises(SystemExit) as cm:
                        nscb.main()
                    self.assertEqual(cm.exception.code, 1)
                    self.assertIn("Error: Profile 'invalid' not found", mock_stderr.getvalue())

if __name__ == '__main__':
    unittest.main()
