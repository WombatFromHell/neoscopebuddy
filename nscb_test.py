#!/usr/bin/python3

import unittest
from unittest.mock import patch
import os
import shutil
from pathlib import Path
import sys
from io import StringIO
from nscb import find_config_file, find_executable, load_config, main

class TestNSCB(unittest.TestCase):

    def setUp(self):
        """Set up a temporary directory for testing."""
        global test_root
        test_root = Path('/tmp/nscb_test')
        test_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        """Clean up after each test."""
        try:
            shutil.rmtree(test_root, ignore_errors=True)
        except OSError as e:
            print(f"Error cleaning up: {e}")

    def test_find_config_file_xdg(self):
        """Test finding config file in XDG_CONFIG_HOME"""
        with patch.dict('os.environ', {'XDG_CONFIG_HOME': str(test_root / 'xdg')}, clear=False):
            Path(test_root / 'xdg').mkdir(parents=True, exist_ok=True)
            Path(test_root / 'xdg' / 'nscb.conf').touch()
            self.assertEqual(find_config_file(), Path(test_root / 'xdg' / 'nscb.conf'))

    def test_find_config_file_home(self):
        """Test finding config file in HOME"""
        with patch.dict('os.environ', {'HOME': str(test_root / 'home')}, clear=False):
            # Clear XDG_CONFIG_HOME to ensure it falls back to HOME
            with patch.dict('os.environ', {'XDG_CONFIG_HOME': ''}, clear=False):
                Path(test_root / 'home' / '.config').mkdir(parents=True, exist_ok=True)
                Path(test_root / 'home' / '.config' / 'nscb.conf').touch()
                self.assertEqual(find_config_file(), Path(test_root / 'home' / '.config' / 'nscb.conf'))

    def test_find_config_file_none(self):
        """Test when config file is not found"""
        with patch.dict('os.environ', {'XDG_CONFIG_HOME': '/nonexistent', 'HOME': '/nonexistent'}, clear=False):
            self.assertIsNone(find_config_file())

    def test_find_executable_found(self):
        """Test finding an executable in PATH"""
        with patch.dict('os.environ', {'PATH': str(test_root / 'bin')}, clear=False):
            Path(test_root / 'bin').mkdir(parents=True, exist_ok=True)
            gamescope_path = Path(test_root / 'bin' / 'gamescope')
            gamescope_path.touch()
            os.chmod(gamescope_path, 0o755)
            self.assertTrue(find_executable('gamescope'))

    def test_find_executable_not_found(self):
        """Test when executable is not found"""
        with patch.dict('os.environ', {'PATH': str(test_root / 'bin')}, clear=False):
            Path(test_root / 'bin').mkdir(parents=True, exist_ok=True)
            self.assertFalse(find_executable('nonexistent'))

    def test_load_config(self):
        """Test loading configuration from file"""
        config_path = Path(test_root / 'nscb.conf')
        config_path.write_text('''# comment
profile1 = value1
profile2 = value2
''')
        expected = {'profile1': 'value1', 'profile2': 'value2'}
        self.assertEqual(load_config(config_path), expected)

    def test_load_config_quoted_values(self):
        """Test loading configuration with quoted values"""
        config_path = Path(test_root / 'nscb.conf')
        config_path.write_text('''# Test quoted and unquoted values
quoted_double = "-W 640 -H 480 --force-grab-cursor"
quoted_single = '-W 1920 -H 1080 --fullscreen'
unquoted = -W 800 -H 600 --windowed
mixed_spaces = "  -W 1024 -H 768  "
''')
        expected = {
            'quoted_double': '-W 640 -H 480 --force-grab-cursor',
            'quoted_single': '-W 1920 -H 1080 --fullscreen', 
            'unquoted': '-W 800 -H 600 --windowed',
            'mixed_spaces': '  -W 1024 -H 768  '
        }
        self.assertEqual(load_config(config_path), expected)

    def test_main_gamescope_not_found(self):
        """Test error handling when gamescope is not found"""
        with patch.dict('os.environ', {'PATH': str(test_root / 'bin')}, clear=False):
            Path(test_root / 'bin').mkdir(parents=True, exist_ok=True)
            with patch('sys.stderr', StringIO()):  # Suppress error output
                with self.assertRaises(SystemExit) as context:
                    with patch.object(sys, 'argv', ['nscb.py']):
                        main()
                self.assertEqual(context.exception.code, 1)

    def test_main_no_config_file_with_profile(self):
        """Test error handling when config file is not found but profile is specified"""
        Path(test_root / 'bin').mkdir(parents=True, exist_ok=True)
        gamescope_path = Path(test_root / 'bin' / 'gamescope')
        gamescope_path.touch()
        os.chmod(gamescope_path, 0o755)
        with patch.dict('os.environ', {'PATH': str(test_root / 'bin'), 'XDG_CONFIG_HOME': '/nonexistent', 'HOME': str(test_root / 'home')}, clear=False):
            with patch('sys.stderr', StringIO()):  # Suppress error output
                with self.assertRaises(SystemExit) as context:
                    with patch.object(sys, 'argv', ['nscb.py', '-p', 'some_profile']):
                        main()
                self.assertEqual(context.exception.code, 1)

    def test_main_no_config_file_without_profile(self):
        """Test that program works when config file is not found but no profile is specified"""
        Path(test_root / 'bin').mkdir(parents=True, exist_ok=True)
        gamescope_path = Path(test_root / 'bin' / 'gamescope')
        gamescope_path.touch()
        os.chmod(gamescope_path, 0o755)
        with patch.dict('os.environ', {'PATH': str(test_root / 'bin'), 'XDG_CONFIG_HOME': '/nonexistent', 'HOME': str(test_root / 'home')}, clear=False):
            with patch('sys.stdout', StringIO()):  # Suppress print output
                with patch.object(sys, 'argv', ['nscb.py', '-f', '--fullscreen']):
                    with patch.object(os, 'execvp') as mock_execvp:
                        main()
                        mock_execvp.assert_called_with('gamescope', ['-f', '--fullscreen'])

    def test_main_with_profile(self):
        """Test handling profile and command-line arguments"""
        # Create config file in XDG_CONFIG_HOME
        xdg_config_dir = test_root / 'xdg'
        xdg_config_dir.mkdir(parents=True, exist_ok=True)
        config_path = xdg_config_dir / 'nscb.conf'
        config_path.write_text('test_profile = -f -o --value1\n')
        #
        # Create gamescope executable
        bin_dir = test_root / 'bin'
        bin_dir.mkdir(parents=True, exist_ok=True)
        gamescope_path = bin_dir / 'gamescope'
        gamescope_path.touch()
        os.chmod(gamescope_path, 0o755)

        # Set up environment and test
        env_vars = {
            'PATH': str(bin_dir),
            'XDG_CONFIG_HOME': str(xdg_config_dir)
        }

        with patch.dict('os.environ', env_vars, clear=False):
            with patch('sys.stdout', StringIO()):  # Suppress print output
                with patch.object(sys, 'argv', ['nscb.py', '-p', 'test_profile', '--', '--fullscreen']):
                    with patch.object(os, 'execvp') as mock_execvp:
                        main()
                        mock_execvp.assert_called_with('gamescope', ['-f', '-o', '--value1', '--', '--fullscreen'])

    def test_main_with_quoted_profile_args(self):
        """Test handling profile with quoted arguments in config"""
        # Create config file with quoted profile arguments
        xdg_config_dir = test_root / 'xdg'
        xdg_config_dir.mkdir(parents=True, exist_ok=True)
        config_path = xdg_config_dir / 'nscb.conf'
        config_path.write_text('vkcube = "-W 640 -H 480 --force-grab-cursor"\n')
        
        # Create gamescope executable
        bin_dir = test_root / 'bin'
        bin_dir.mkdir(parents=True, exist_ok=True)
        gamescope_path = bin_dir / 'gamescope'
        gamescope_path.touch()
        os.chmod(gamescope_path, 0o755)

        # Set up environment and test
        env_vars = {
            'PATH': str(bin_dir),
            'XDG_CONFIG_HOME': str(xdg_config_dir)
        }

        with patch.dict('os.environ', env_vars, clear=False):
            with patch('sys.stdout', StringIO()):  # Suppress print output
                with patch.object(sys, 'argv', ['nscb.py', '-p', 'vkcube', '--', 'vkcube']):
                    with patch.object(os, 'execvp') as mock_execvp:
                        main()
                        # Should split the quoted arguments properly
                        mock_execvp.assert_called_with('gamescope', ['-W', '640', '-H', '480', '--force-grab-cursor', '--', 'vkcube'])

    def test_main_with_unquoted_profile_args(self):
        """Test handling profile with unquoted arguments in config"""
        # Create config file with unquoted profile arguments  
        xdg_config_dir = test_root / 'xdg'
        xdg_config_dir.mkdir(parents=True, exist_ok=True)
        config_path = xdg_config_dir / 'nscb.conf'
        config_path.write_text('gaming = -W 1920 -H 1080 --fullscreen\n')
        
        # Create gamescope executable
        bin_dir = test_root / 'bin'
        bin_dir.mkdir(parents=True, exist_ok=True)
        gamescope_path = bin_dir / 'gamescope'
        gamescope_path.touch()
        os.chmod(gamescope_path, 0o755)

        # Set up environment and test
        env_vars = {
            'PATH': str(bin_dir),
            'XDG_CONFIG_HOME': str(xdg_config_dir)
        }

        with patch.dict('os.environ', env_vars, clear=False):
            with patch('sys.stdout', StringIO()):  # Suppress print output
                with patch.object(sys, 'argv', ['nscb.py', '-p', 'gaming', 'steam']):
                    with patch.object(os, 'execvp') as mock_execvp:
                        main()
                        # Should split the unquoted arguments properly
                        mock_execvp.assert_called_with('gamescope', ['-W', '1920', '-H', '1080', '--fullscreen', 'steam'])

    def test_main_unknown_profile(self):
        """Test handling unknown profile"""
        # Create config file in XDG_CONFIG_HOME
        xdg_config_dir = test_root / 'xdg'
        xdg_config_dir.mkdir(parents=True, exist_ok=True)
        config_path = xdg_config_dir / 'nscb.conf'
        config_path.write_text('known_profile = value\n')
        #
        # Create gamescope executable
        bin_dir = test_root / 'bin'
        bin_dir.mkdir(parents=True, exist_ok=True)
        gamescope_path = bin_dir / 'gamescope'
        gamescope_path.touch()
        os.chmod(gamescope_path, 0o755)
        #
        # Set up environment and test
        env_vars = {
            'PATH': str(bin_dir),
            'XDG_CONFIG_HOME': str(xdg_config_dir)
        }

        with patch.dict('os.environ', env_vars, clear=False):
            with patch('sys.stderr', StringIO()):  # Suppress error output
                with patch.object(sys, 'argv', ['nscb.py', '-p', 'unknown_profile']):
                    with self.assertRaises(SystemExit) as context:
                        main()
                    self.assertEqual(context.exception.code, 1)

if __name__ == '__main__':
    unittest.main()
