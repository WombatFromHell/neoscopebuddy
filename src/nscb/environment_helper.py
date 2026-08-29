"""Environment variable operations for NeoscopeBuddy."""

import os
import subprocess
import sys


def debug_log(message: str) -> None:
    """Log debug message when NSCB_DEBUG=1 is set."""
    if os.environ.get("NSCB_DEBUG", "").lower() in ("1", "true", "yes", "on"):
        print(f"[DEBUG] {message}", file=sys.stderr, flush=True)


class EnvironmentHelper:
    """Utility class for environment variable operations."""

    @staticmethod
    def get_pre_post_commands() -> tuple[str, str]:
        """Get pre/post commands from environment."""
        # Check new variable names first, then fall back to legacy names
        pre_cmd = os.environ.get("NSCB_PRE_CMD") or os.environ.get("NSCB_PRECMD", "")
        post_cmd = os.environ.get("NSCB_POST_CMD") or os.environ.get("NSCB_POSTCMD", "")
        return pre_cmd.strip(), post_cmd.strip()

    @staticmethod
    def get_framelimit() -> "int | None":
        """Read NSCB_FRAMELIMIT; returns a positive int or None (invalid ignored)."""
        raw = os.environ.get("NSCB_FRAMELIMIT")
        if raw is None:
            return None
        try:
            value = int(raw)
        except ValueError:
            debug_log(f"get_framelimit: ignoring non-integer NSCB_FRAMELIMIT={raw!r}")
            return None
        if value <= 0:
            debug_log(f"get_framelimit: ignoring non-positive NSCB_FRAMELIMIT={value}")
            return None
        return value

    @staticmethod
    def is_gamescope_active() -> bool:
        """Return True if a gamescope session is already running."""
        if os.environ.get("XDG_CURRENT_DESKTOP") == "gamescope":
            return True
        # ponytail: pgrep -x matches the exact process name, replacing the
        # brittle ps-text scan whose substring match could catch unrelated
        # lines. pgrep exits 1 when nothing matches (reported as
        # CalledProcessError); any other failure -> assume not active.
        try:
            subprocess.check_output(
                ["pgrep", "-x", "gamescope"], stderr=subprocess.STDOUT
            )
            return True
        except subprocess.CalledProcessError:
            return False
        except Exception:
            return False

    @staticmethod
    def force_nested() -> bool:
        """Return True if NSCB_FORCE_NESTED=1 asks for a nested gamescope launch."""
        return os.environ.get("NSCB_FORCE_NESTED", "").lower() in (
            "1",
            "true",
            "yes",
            "on",
        )

    @staticmethod
    def should_disable_ld_preload_wrap() -> bool:
        """Check if LD_PRELOAD wrapping should be disabled."""
        disable_var = os.environ.get("NSCB_DISABLE_LD_PRELOAD_WRAP", "").lower()
        faugus_log = os.environ.get("FAUGUS_LOG")

        debug_log(
            f"should_disable_ld_preload_wrap: NSCB_DISABLE_LD_PRELOAD_WRAP={disable_var}"
        )
        debug_log(f"should_disable_ld_preload_wrap: FAUGUS_LOG={faugus_log}")

        if disable_var in ("1", "true", "yes", "on"):
            debug_log(
                "should_disable_ld_preload_wrap: LD_PRELOAD wrapping disabled via NSCB_DISABLE_LD_PRELOAD_WRAP"
            )
            return True
        #
        # Automatically disable LD_PRELOAD wrapping when launched with faugus-launcher
        # by checking for the FAUGUS_LOG environment variable
        if faugus_log is not None:
            debug_log(
                "should_disable_ld_preload_wrap: LD_PRELOAD wrapping disabled via FAUGUS_LOG (faugus-launcher detected)"
            )
            return True
        return False
