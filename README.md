# NeoScopebuddy [![Coverage Status](./coverage-badge.svg?dummy=8484744)]()

NeoScopebuddy is a thin wrapper around the gamescope utility, just like its competitor scopebuddy, except it supports a critical extra feature: profiles!

Profiles are defined in `$HOME/.config/nscb.conf` using simple `KEY=VALUE` lines, and called via `-p <name>` or `--profile <name>`:

```ini
someapp=-f -W 1280 -H 720
someotherapp=-b -W 1920 -H 1080
```

## Example usage

```bash
nscb.py -p someapp -- /usr/bin/someapp
```

Profiles can also be used with pass-through arguments and the arguments will override the profile:

```bash
nscb.py -p someapp -W 3840 -H 2160 --hdr-enabled -- /usr/bin/someapp
```

Alternatively, multiple profiles can be chained together and the last one will overwrite conflicting exclusive arguments from the others:

```bash
nscb.py -p someapp -p someotherapp -- /usr/bin/someapp
```

You can also use the syntax `--profiles=profile1,profile2` to chain multiple profiles:

```bash
nscb.py --profiles=profile1,profile2 -- /usr/bin/someapp
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
