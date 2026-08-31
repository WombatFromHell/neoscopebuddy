#!/bin/sh
# ponytail: save LD_PRELOAD before stripping for python; re-inject only for app (polyglot.py:8-21 contract: LD_PRELOAD_SAVED="$LD_PRELOAD"; env -u LD_PRELOAD; gamescope -- env LD_PRELOAD=$SAVED). LD_LIBRARY_PATH is passthrough (Heroic mount) and must not trigger LD_PRELOAD handling.
LD_PRELOAD_SAVED="$LD_PRELOAD"
case "${NSCB_DEBUG:-}" in 1|true|True|yes|on|ON) _m="[DEBUG] polyglot: argv=$* a0=$0 real=$(readlink -f "$0" 2>/dev/null || echo "$0") LD_PRELOAD=$LD_PRELOAD -> NSCB_ORIG_LD_PRELOAD=$LD_PRELOAD_SAVED LD_LIBRARY_PATH=$LD_LIBRARY_PATH (passthrough)"; echo "$_m" >&2; echo "$_m" >> "${XDG_RUNTIME_DIR:-/tmp}/nscb.log" 2>/dev/null || true;; esac
exec env -u LD_PRELOAD NSCB_ORIG_LD_PRELOAD="$LD_PRELOAD_SAVED" /usr/bin/python3 "$(readlink -f "$0" 2>/dev/null || echo "$0")" "$@"
