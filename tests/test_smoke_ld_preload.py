"""Smoketest reproducing LD_PRELOAD handling issue.

Polyglot contract (polyglot.py:8-22,65-74):
  LD_PRELOAD_SAVED="$LD_PRELOAD"
  exec env -u LD_PRELOAD NSCB_ORIG_LD_PRELOAD="$LD_PRELOAD_SAVED" python3 "$0" "$@"
  gamescope <args> -- env LD_PRELOAD=$LD_PRELOAD_SAVED <game>

Current bug: LD_LIBRARY_PATH=/tmp/.mount... with LD_PRELOAD='' makes
_check_ld_preload_status return True and strips/re-injects LD_LIBRARY_PATH.
Expected: has_ld_preload=False when LD_PRELOAD empty, so built command is
  gamescope ... -- linuwux ...
not
  env -u LD_PRELOAD -u LD_LIBRARY_PATH gamescope ... -- env LD_LIBRARY_PATH=...
"""

from unittest.mock import patch


def test_smoke_empty_preload_with_ld_library_path(monkeypatch):
    """Reproduces user log: LD_PRELOAD='', LD_LIBRARY_PATH='/tmp/.mount...'."""
    # Simulate polyglot shim having saved LD_LIBRARY_PATH but not LD_PRELOAD
    monkeypatch.setenv("NSCB_ORIG_LD_PRELOAD", "")
    monkeypatch.setenv("NSCB_ORIG_LD_LIBRARY_PATH", "/tmp/.mount_heroictMw5Ia/usr/lib:")
    monkeypatch.delenv("LD_PRELOAD", raising=False)
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)
    monkeypatch.delenv("NSCB_DISABLE_LD_PRELOAD_WRAP", raising=False)
    monkeypatch.delenv("FAUGUS_LOG", raising=False)
    monkeypatch.delenv("NSCB_DEBUG", raising=False)

    from nscb.command_executor import CommandExecutor

    has = CommandExecutor._check_ld_preload_status()
    # BUG: has is True because LD_LIBRARY_PATH triggers it; should be False
    assert has is False, (
        f"has_ld_preload should be False when LD_PRELOAD empty, got {has}"
    )

    # Inactive command should NOT have env -u prefix nor LD_LIBRARY_PATH re-inject
    # Mock DisplayDetector to avoid auto-res noise
    with patch(
        "nscb.command_executor.DisplayDetector.get_resolution", return_value=None
    ):
        cmd = CommandExecutor._build_inactive_gamescope_command(
            ["-f", "--", "linuwux", "/usr/bin/umu-run", "game.exe"], "", ""
        )
    assert "env -u LD_PRELOAD" not in cmd, (
        f"should not strip LD_PRELOAD when empty, got {cmd!r}"
    )
    assert "LD_LIBRARY_PATH" not in cmd, (
        f"should not mention LD_LIBRARY_PATH when LD_PRELOAD is empty, got {cmd!r}"
    )
    assert "gamescope -f -- linuwux" in cmd, (
        f"expected plain gamescope wrap, got {cmd!r}"
    )


def test_smoke_with_preload(monkeypatch):
    """When LD_PRELOAD is set via shim, it must be stripped for gamescope and re-injected for app."""
    monkeypatch.setenv("NSCB_ORIG_LD_PRELOAD", "/tmp/fake.so")
    monkeypatch.setenv("NSCB_ORIG_LD_LIBRARY_PATH", "")
    monkeypatch.delenv("LD_PRELOAD", raising=False)
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)
    monkeypatch.delenv("NSCB_DISABLE_LD_PRELOAD_WRAP", raising=False)
    monkeypatch.delenv("FAUGUS_LOG", raising=False)

    from nscb.command_executor import CommandExecutor

    has = CommandExecutor._check_ld_preload_status()
    assert has is True

    with patch(
        "nscb.command_executor.DisplayDetector.get_resolution", return_value=None
    ):
        cmd = CommandExecutor._build_inactive_gamescope_command(
            ["-f", "--", "myapp"], "", ""
        )
    assert "env -u LD_PRELOAD gamescope" in cmd, (
        f"gamescope should be stripped, got {cmd!r}"
    )
    assert "env LD_PRELOAD=/tmp/fake.so myapp" in cmd, (
        f"app should re-inject, got {cmd!r}"
    )
    assert "LD_LIBRARY_PATH" not in cmd, (
        "should not touch LD_LIBRARY_PATH when only LD_PRELOAD set"
    )


def test_smoke_active_gamescope_restores_preload(monkeypatch):
    """Active-path (nested nscb inside gamescope) must restore LD_PRELOAD too.

    Root cause: the shim always strips LD_PRELOAD before python starts, and NSCB
    launches gamescope itself with env -u LD_PRELOAD, so an active session never
    inherits it. The old noop path passed app args verbatim -> game ran with no
    LD_PRELOAD (only NSCB_ORIG_LD_PRELOAD present, matching the /proc environ).
    """
    saved = (
        "/run/host/usr/lib/extest/libextest.so:"
        "/var/home/josh/.local/share/Steam/steamrt64/gameoverlayrenderer.so:"
        "/var/home/josh/.local/share/Steam/steamrt32/gameoverlayrenderer.so:"
        "/home/josh/.local/lib/liblinuwux.so"
    )
    monkeypatch.setenv("NSCB_ORIG_LD_PRELOAD", saved)
    monkeypatch.delenv("LD_PRELOAD", raising=False)
    monkeypatch.delenv("NSCB_DISABLE_LD_PRELOAD_WRAP", raising=False)
    monkeypatch.delenv("FAUGUS_LOG", raising=False)

    from nscb.command_executor import CommandExecutor

    with patch(
        "nscb.command_executor.DisplayDetector.get_resolution", return_value=None
    ):
        cmd = CommandExecutor._build_active_gamescope_command(
            ["-f", "--", "forza"], "", ""
        )
    assert f"env LD_PRELOAD={saved} forza" in cmd, (
        f"active path must re-inject LD_PRELOAD, got {cmd!r}"
    )


def test_smoke_active_gamescope_no_preload_verbatim(monkeypatch):
    """No preload anywhere -> active path is a pure no-op."""
    monkeypatch.delenv("NSCB_ORIG_LD_PRELOAD", raising=False)
    monkeypatch.delenv("LD_PRELOAD", raising=False)
    monkeypatch.delenv("NSCB_DISABLE_LD_PRELOAD_WRAP", raising=False)
    monkeypatch.delenv("FAUGUS_LOG", raising=False)

    from nscb.command_executor import CommandExecutor

    with patch(
        "nscb.command_executor.DisplayDetector.get_resolution", return_value=None
    ):
        cmd = CommandExecutor._build_active_gamescope_command(
            ["-f", "--", "forza"], "", ""
        )
    assert cmd == "forza", f"expected verbatim app, got {cmd!r}"


def test_smoke_debug_captures_saved(monkeypatch, tmp_path):
    """NSCB_DEBUG=1 must capture saved LD_PRELOAD to XDG_RUNTIME_DIR/nscb.log and stderr."""
    monkeypatch.setenv("NSCB_DEBUG", "1")
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    monkeypatch.setenv("NSCB_ORIG_LD_PRELOAD", "/tmp/saved.so")
    monkeypatch.delenv("LD_PRELOAD", raising=False)

    from nscb.environment_helper import debug_log

    log = tmp_path / "nscb.log"
    debug_log("startup: test saved capture NSCB_ORIG_LD_PRELOAD='/tmp/saved.so'")
    assert log.exists()
    assert "NSCB_ORIG_LD_PRELOAD" in log.read_text()
    assert "/tmp/saved.so" in log.read_text()
