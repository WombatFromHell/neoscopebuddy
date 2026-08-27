"""Auto-detect the active display resolution for NSCB_AUTO_RES.

Uses stdlib json + subprocess (no jq dependency). Supports niri
(`niri msg --json outputs`) and KDE (`kscreen-doctor -j`).
"""

import json
import os
import shutil
import subprocess

from .types import ArgsList


class DisplayDetector:
    """Query the active display's current mode for auto-resolution."""

    RES_FLAGS = {
        "-w",
        "--width",
        "-h",
        "--height",
        "-W",
        "--output-width",
        "-H",
        "--output-height",
    }
    PREFER_FLAGS = {"-O", "--prefer-output"}

    @staticmethod
    def detect_backend() -> str:
        if os.environ.get("XDG_CURRENT_DESKTOP") == "niri" and shutil.which("niri"):
            return "niri"
        if os.environ.get("KDE_FULL_SESSION") and shutil.which("kscreen-doctor"):
            return "kde"
        return "none"

    @staticmethod
    def get_resolution(prefer: str | None = None) -> tuple[int, int] | None:
        backend = DisplayDetector.detect_backend()
        if backend == "niri":
            return DisplayDetector._niri(prefer)
        if backend == "kde":
            return DisplayDetector._kde(prefer)
        return None

    @staticmethod
    def _niri(prefer: str | None) -> tuple[int, int] | None:
        try:
            out = subprocess.check_output(
                ["niri", "msg", "--json", "outputs"], text=True
            )
        except Exception:
            return None
        outputs = DisplayDetector._parse_niri(out)
        if not outputs:
            return None
        disp = DisplayDetector._pick(
            outputs,
            prefer,
            lambda o: o.get("logical") is not None,
            lambda o: (o["logical"]["x"], o["logical"]["y"]),
        )
        if disp is None or disp.get("current_mode") is None:
            return None
        mode = disp["modes"][disp["current_mode"]]
        return mode["width"], mode["height"]

    @staticmethod
    def _parse_niri(out: str) -> list:
        # niri returns a single JSON object keyed by connector name; older/other
        # builds may emit a JSON array or newline-separated objects.
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            data = [json.loads(line) for line in out.splitlines() if line.strip()]
        if isinstance(data, dict):
            return list(data.values())
        return data

    @staticmethod
    def _kde(prefer: str | None) -> tuple[int, int] | None:
        try:
            data = json.loads(
                subprocess.check_output(["kscreen-doctor", "-j"], text=True)
            )
        except Exception:
            return None
        outs = data.get("outputs", [])
        disp = DisplayDetector._pick(
            outs,
            prefer,
            lambda o: o.get("enabled"),
            lambda o: o.get("priority", 0),
        )
        if disp is None:
            return None
        mode = next(
            (
                m
                for m in disp.get("modes", [])
                if m.get("id") == disp.get("currentModeId")
            ),
            None,
        )
        if mode is None:
            return None
        return mode["size"]["width"], mode["size"]["height"]

    @staticmethod
    def _pick(items, prefer, enabled_fn, sort_key):
        """Select the display: by name when prefer given, else primary."""
        if prefer:
            return next((o for o in items if o.get("name") == prefer), None)
        enabled = [o for o in items if enabled_fn(o)]
        if not enabled:
            return items[0] if items else None
        return sorted(enabled, key=sort_key)[0]

    @staticmethod
    def has_resolution_flag(args: ArgsList) -> bool:
        for tok in args:
            if tok in DisplayDetector.RES_FLAGS:
                return True
            if any(tok.startswith(f"{n}=") for n in DisplayDetector.RES_FLAGS):
                return True
        return False

    @staticmethod
    def extract_prefer_output(args: ArgsList) -> str | None:
        i = 0
        while i < len(args):
            tok = args[i]
            if tok in DisplayDetector.PREFER_FLAGS and i + 1 < len(args):
                return args[i + 1]
            if any(tok.startswith(f"{n}=") for n in DisplayDetector.PREFER_FLAGS):
                return tok.split("=", 1)[1]
            i += 1
        return None
