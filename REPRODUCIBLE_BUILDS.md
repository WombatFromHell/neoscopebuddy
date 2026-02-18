# Reproducible Builds

NeoscopeBuddy produces bitwise-identical artifacts across different build environments when given the same source and build parameters.

## Quick Start

```bash
make build                    # Build with default SOURCE_DATE_EPOCH
export SOURCE_DATE_EPOCH=123  # Or set custom epoch
make build
cd dist && sha256sum -c nscb.pyz.sha256sum  # Verify
```

## Configuration

| Variable            | Default     | Description                                     |
| ------------------- | ----------- | ----------------------------------------------- |
| `SOURCE_DATE_EPOCH` | `315532800` | Timestamp for reproducibility (Jan 1, 1980 UTC) |
| `VERSION`           | auto        | Extracted from `pyproject.toml`                 |

## Build Workflow

1. **Stage**: Copy `src/` to `dist/staging/`
2. **Inject**: Set version in `application.py` (staging only)
3. **Entry**: Create `__main__.py` with `from entry import main; main()`
4. **Normalize**: Set all mtimes to `SOURCE_DATE_EPOCH`
5. **Archive**: `find | LC_ALL=C sort | zip -X` for deterministic ordering
6. **Bundle**: Prepend shebang, create executable
7. **Verify**: Generate SHA256 checksum

## Guarantees

**Reproducible:**

- File ordering via `LC_ALL=C sort`
- Timestamps via `SOURCE_DATE_EPOCH`
- ZIP metadata stripped with `zip -X`

**Not reproducible:**

- Different `SOURCE_DATE_EPOCH` values
- Different versions (embedded in build)

## Verification

```bash
# Same-source reproducibility
make clean build && cp dist/nscb.pyz.sha256sum /tmp/a.sum
make clean build && diff dist/nscb.pyz.sha256sum /tmp/a.sum  # No diff = identical

# Cross-system verification
# Build on system A, copy checksum to system B
# Build on system B, compare checksums
```

## Why Custom Workflow?

Python's `zipapp` module doesn't guarantee:

- Deterministic file ordering
- Reproducible timestamps
- Namespace package support

The custom Makefile workflow provides full control over all build aspects.

## Troubleshooting

| Issue               | Solution                                             |
| ------------------- | ---------------------------------------------------- |
| Different checksums | Ensure same `SOURCE_DATE_EPOCH`, source, and version |
| Verification fails  | Run `make clean build` to rebuild                    |
