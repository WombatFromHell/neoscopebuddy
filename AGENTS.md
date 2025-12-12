# Neoscope Buddy (nscb) - Agentic Tool Guide

## Development Environment Tools

### Build System

- **Build zipapp package**: `make clean build` - Creates `./dist/nscb.pyz` using Python's `zipapp` module
- **Install locally**: `make all` - Cleans the dev environment, builds, and installs to `~/.local/bin` with `nscb` symlink

### Code Quality Tools

- **Run tests**: `make test` - Executes test suite using uv and pytest
- **Code quality checks**: `make quality` - Runs ruff and pyright for linting and type checking
- **Complexity metrics**: `make radon` - Analyzes code complexity

## Test Environment Tools

### Test Execution

- **Run specific tests**: `uv run pytest -xvs tests/test_module.py` - Execute tests for a specific module
- **Run with coverage**: `uv run pytest --cov=src --cov-report=term-missing --cov-branch` - Generate coverage report
- **Debug tests**: `uv run pytest -xvs` - Verbose output with stdout capture disabled

### Test Development

- **Add new tests**: Follow existing patterns in `tests/test_*.py` files
- **Use mocking**: Utilize `pytest-mock` fixture for dependency isolation
- **Test categories**: Use appropriate decorators (`@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`)

## Workflow Considerations

- **Test-driven development**: Write tests before implementing new features
- **Quality gates**: Run `make quality` to ensure linting/formatting validates code before committing changes
- **Test validation**: Ensure all tests pass before considering work complete
- **Debugging**: Use `NSCB_DEBUG=1` environment variable for detailed logging
