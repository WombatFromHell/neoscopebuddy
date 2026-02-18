# Neoscope Buddy (nscb) - Agent Guide

**Profile-based gamescope wrapper utility** - Manages gamescope configurations via profiles with argument merging and override support.

## Quick Commands

```bash
make all          # Clean, build, install to ~/.local/bin
make build        # Create dist/nscb.pyz (reproducible build)
make test         # Run pytest with coverage
make quality      # Run ty + ruff (type check + lint/format)
make radon        # Code complexity metrics
```

## Build System

- **Custom bundle workflow** (not zipapp) for bitwise-reproducible builds
- Uses `SOURCE_DATE_EPOCH` (default: `315532800`) for deterministic timestamps
- Version auto-extracted from `pyproject.toml`
- SHA256 checksum generated at `dist/nscb.pyz.sha256sum`

## Testing

- **Framework**: pytest with uv
- **Markers**: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`
- **Mocking**: pytest-mock fixture
- **Debug**: `NSCB_DEBUG=1` for detailed logging

## Code Quality

- **Type checker**: ty
- **Linter/Formatter**: ruff
- **Enforcement**: `make quality` must pass before commits

## Project Structure

```
src/
├── entry.py              # Zipapp entry point
└── nscb/
    ├── application.py    # Main orchestrator
    ├── profile_manager.py
    ├── config_manager.py
    ├── command_executor.py
    ├── argument_processor.py
    ├── system_detector.py
    ├── environment_helper.py
    ├── gamescope_args.py
    ├── path_helper.py
    ├── types.py
    └── exceptions.py
```

## Key Conventions

- **TDD**: Write tests before features
- **Quality gates**: Run `make quality` before committing
- **Test validation**: All tests must pass
- **Documentation**: See DESIGN.md (architecture) and REPRODUCIBLE_BUILDS.md (build system)
