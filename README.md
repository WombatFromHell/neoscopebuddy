# NeoScopebuddy

NeoScopebuddy is a thin wrapper around the gamescope utility, just like its competitor scopebuddy, except it supports a critical extra feature: profiles!

Profiles are defined in `$HOME/.config/nscb.conf` using simple `KEY=VALUE` lines, and called via `-p <name>` or `--profile <name>`:

```ini
someapp=-f -W 1280 -H 720
```

## Example usage

```bash
nscb.py -p someapp -- /usr/bin/someapp
```

Profiles can also be used with pass-through arguments and the arguments will override the profile:

```bash
nscb.py -p someapp -W 3840 -H 2160 --hdr-enabled -- /usr/bin/someapp
```

## Direct pass-through

If no profile is specified, arguments are passed through to `gamescope` as-is:

```bash
nscb.py -f -W 1280 -H 720 -- /usr/bin/someapp
```

Is the same as:

```bash
gamescope -f -W 1280 -H 720 -- /usr/bin/someapp
```
