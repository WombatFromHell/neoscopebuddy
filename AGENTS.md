# Neoscope Buddy (nscb) - Agentic Coding Guide

## Project Overview

Neoscope Buddy (`nscb.pyz`) is a Python-based gamescope wrapper that provides a profile-based configuration system for managing gamescope settings. It allows users to define reusable gamescope configurations in a config file and apply them via command-line arguments with support for overrides.

## Key Agentic Coding Information

### Configuration Format

- Config file uses `KEY=VALUE` format at `$XDG_CONFIG_HOME/nscb.conf` or `$HOME/.config/nscb.conf`
- Keys represent profile names, values are space-separated gamescope arguments
- Example: `gaming=-f -W 1920 -H 1080`

### Critical Functions to Understand

- `merge_arguments`: Implements sophisticated argument merging with conflict resolution
- `find_config_file` / `load_config`: Configuration loading and parsing
- `parse_profile_args`: Profile argument parsing
- `execute_gamescope_command`: Command execution logic

### Argument Merging Rules

- Override arguments take precedence over profile arguments
- Mutually exclusive flags like `-f` (fullscreen) vs `--borderless` are handled properly
- Non-conflicting flags from profiles are preserved unless explicitly overridden
- Order of arguments is maintained in the final command

### Project Tools

- Run our 'zipapp' bundler build: `make clean build`
- Run tests and code coverage: `make test`
- Run code complexity metrics `make radon`
- Lint and format: `make quality`

## Development Guidelines

### Adding New Features

- Update `GAMESCOPE_ARGS_MAP` for new gamescope argument mappings
- Add appropriate unit tests for new functionality
- Test with profile system and override functionality

### Security Considerations

- Use `shlex.quote()` when building command strings to prevent injection
- Sanitize user input from config files

### Development Workflow Considerations

- Ensure the 'code coverage' command above is used when adding/removing/refactoring tests
- Ensure the 'lint and format' command above is used when refactoring any python code in this project
- Ensure the 'format markdown' command above is used when refactoring any markdown file in this project
- Before considering a task, action plan, or code change to be 'complete' or 'successful' ensure we run our tests using the 'run tests' command above
- Try to fix a persistently failing test 3 times before prompting the user on what we should do next
