# NeoScopebuddy

NeoScopebuddy is a thin wrapper around the gamescope utility, just like its competitor scopebuddy, except it supports a critical extra feature: profiles!

## Usage

```bash
nscb.pyz [-p profile[,...]] [--profile=profile[,...]]
         [--profiles=profile[,...]] [gamescope flags] [-- app...]
```

If `--` is present, everything after it is passed to the application. Gamescope flags before `--` override matching profile flags.

## Profiles

```bash
nscb.pyz -p gaming -- /usr/bin/mygame              # single profile
nscb.pyz -p gaming -W 2560 -H 1440 -- /usr/bin/mygame  # profile + overrides
nscb.pyz -p gaming -p quiet -- /usr/bin/mygame     # multiple profiles
nscb.pyz --profiles=gaming,quiet -- /usr/bin/mygame     # comma-separated
```

Reserved profile names: `help`, `export`.

## Configuration File

Path: `$XDG_CONFIG_HOME/nscb.conf` or `~/.config/nscb.conf`

Sections group args and exports per profile:

```ini
[gaming]
-f -W 1920 -H 1080
export MANGOHUD=1

[quiet]
-b

# Global exports (before any section) always apply:
export DISPLAY=:0
```

Legacy flat syntax still works:

```ini
gaming=-f -W 1920 -H 1080
export MANGOHUD=1
```

Lines starting with `#` are comments. Quoted values have quotes stripped.

## Environment Variables

| Variable                         | Description                                                |
| -------------------------------- | ---------------------------------------------------------- |
| `NSCB_PRE_CMD`                   | Command to run before gamescope                            |
| `NSCB_POST_CMD`                  | Command to run after gamescope exits                       |
| `NSCB_DEBUG=1`                   | Enable debug logging to stderr                             |
| `NSCB_DISABLE_LD_PRELOAD_WRAP=1` | Skip preserving LD_PRELOAD to child process                |
| `FAUGUS_LOG`                     | Auto-disables LD_PRELOAD wrapping (set by faugus-launcher) |

Legacy names `NSCB_PRECMD` and `NSCB_POSTCMD` also work.

## Direct Pass-Through

Without a profile, arguments pass through to gamescope as-is:

```bash
nscb.pyz -f -W 1280 -H 720 -- /usr/bin/mygame
# equivalent to: gamescope -f -W 1280 -H 720 -- /usr/bin/mygame
```

## Building

```bash
make build       # local deterministic build → dist/nscb.pyz
make build-nix   # reproducible Nix build
make install     # install to ~/.local/bin with nscb symlink
```
