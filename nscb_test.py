#!/usr/bin/python3
import unittest
from unittest.mock import patch
import os
import sys
import tempfile
from pathlib import Path

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

    def test_find_config_file_home(self):
        """Test finding config file in HOME/.config."""
        home_dir = os.path.join(self.temp_dir.name, 'home')
        config_dir = os.path.join(home_dir, '.config')
        os.makedirs(config_dir)
        config_path = os.path.join(config_dir, 'nscb.conf')

        with open(config_path, 'w') as f:
            f.write('test=value')

        with patch.dict(os.environ, {'HOME': home_dir}):
            result = nscb.find_config_file()
            self.assertEqual(result, Path(config_path))

    def test_find_config_file_not_found(self):
        """Test when config file is not found."""
        result = nscb.find_config_file()
        self.assertIsNone(result)

    @patch('os.environ', {'PATH': '/usr/bin:/bin'})
    @patch('os.access')
    def test_find_gamescope_found(self, mock_access):
        """Test finding gamescope when it exists and is executable."""
        mock_access.return_value = True
        result = nscb.find_gamescope()
        self.assertTrue(result)

    @patch('os.environ', {'PATH': '/usr/bin:/bin'})
    @patch('os.access')
    def test_find_gamescope_not_found(self, mock_access):
        """Test when gamescope is not found."""
        mock_access.return_value = False
        result = nscb.find_gamescope()
        self.assertFalse(result)

    def test_load_config(self):
        """Test loading config file."""
        config_content = '''# This is a comment
test=value
profile1=arg1 arg2
profile2=arg3
'''
        config_path = os.path.join(self.temp_dir.name, 'nscb.conf')
        with open(config_path, 'w') as f:
            f.write(config_content)

        expected_config = {
            'test': 'value',
            'profile1': 'arg1 arg2',
            'profile2': 'arg3'
        }

        result = nscb.load_config(config_path)
        self.assertEqual(result, expected_config)

    def test_load_config_empty(self):
        """Test loading empty config file."""
        config_path = os.path.join(self.temp_dir.name, 'nscb.conf')
        with open(config_path, 'w') as f:
            f.write('')

        result = nscb.load_config(config_path)
        self.assertEqual(result, {})

    @patch('nscb.find_gamescope')
    @patch('sys.argv', ['nscb.py', '--profile', 'test', 'app', 'arg1'])
    def test_main_success(self, mock_find_gamescope):
        """Test main function success path."""
        mock_find_gamescope.return_value = True

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

    @patch('nscb.find_gamescope')
    def test_main_no_gamescope(self, mock_find_gamescope):
        """Test main function when gamescope is not found."""
        mock_find_gamescope.return_value = False

        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            with self.assertRaises(SystemExit) as cm:
                nscb.main()
            self.assertEqual(cm.exception.code, 1)
            self.assertIn("Error: gamescope not found in PATH or is not executable", mock_stderr.getvalue())

    @patch('nscb.find_gamescope')
    def test_main_no_config(self, mock_find_gamescope):
        """Test main function when config file is not found."""
        mock_find_gamescope.return_value = True

        with patch.dict(os.environ, {'XDG_CONFIG_HOME': '/nonexistent'}):
            with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
                with self.assertRaises(SystemExit) as cm:
                    nscb.main()
                self.assertEqual(cm.exception.code, 1)
                self.assertIn("Error: Could not find nscb.conf", mock_stderr.getvalue())

    @patch('nscb.find_gamescope')
    def test_main_invalid_profile(self, mock_find_gamescope):
        """Test main function with invalid profile."""
        mock_find_gamescope.return_value = True

        config_content = '''profile1=arg1'''
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
    import unittest
    from io import StringIO

    unittest.main()

