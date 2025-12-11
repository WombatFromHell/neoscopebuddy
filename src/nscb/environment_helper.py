"""Environment variable operations for NeoscopeBuddy."""

import os
import subprocess
import sys

from .types import CommandTuple


def debug_log(message: str) -> None:
    """Log debug message when NSCB_DEBUG=1 is set."""
    if os.environ.get("NSCB_DEBUG", "").lower() in ("1", "true", "yes", "on"):
        print(f"[DEBUG] {message}", file=sys.stderr, flush=True)


class EnvironmentHelper:
    """Utility class for environment variable operations."""

    @staticmethod
    def get_pre_post_commands() -> CommandTuple:
        """Get pre/post commands from environment."""
        # Check new variable names first, then fall back to legacy names
        pre_cmd = os.environ.get("NSCB_PRE_CMD") or os.environ.get("NSCB_PRECMD", "")
        post_cmd = os.environ.get("NSCB_POST_CMD") or os.environ.get("NSCB_POSTCMD", "")
        return pre_cmd.strip(), post_cmd.strip()

    @staticmethod
    def is_gamescope_active() -> bool:
        """Determine if system runs under gamescope."""
        # Check XDG_CURRENT_DESKTOP first (more reliable than ps check)
        if os.environ.get("XDG_CURRENT_DESKTOP") == "gamescope":
            return True

        try:
            output = subprocess.check_output(
                ["ps", "ax"], stderr=subprocess.STDOUT, text=True
            )
            # More precise checking for gamescope process
            lines = output.split("\n")
            for line in lines:
                if "gamescope" in line and "grep" not in line:
                    return True
        except Exception:
            pass

        return False

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
