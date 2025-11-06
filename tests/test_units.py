from pathlib import Path
from unittest.mock import patch

import pytest

from nscb import (
    find_executable,
    merge_arguments,
    merge_multiple_profiles,
    parse_profile_args,
    separate_flags_and_positionals,
)


@pytest.mark.unit
def test_parse_profile_args():
    """Test profile argument parsing variations"""
    assert parse_profile_args(["-p", "gaming"]) == (["gaming"], [])
    assert parse_profile_args(["--profile=streaming"]) == (["streaming"], [])
    assert parse_profile_args(["-p", "a", "--profile=b", "cmd"]) == (
        ["a", "b"],
        ["cmd"],
    )
    assert parse_profile_args(["--profiles=gaming,streaming"]) == (
        ["gaming", "streaming"],
        [],
    )
    assert parse_profile_args(["--profiles="]) == ([], [])


@pytest.mark.unit
def test_separate_flags_and_positionals_basic():
    """Basic flag and positional separation"""
    flags, positionals = separate_flags_and_positionals(["-W", "1920", "--nested"])
    assert flags == [("-W", "1920"), ("--nested", None)]
    assert positionals == []


@pytest.mark.unit
def test_separate_flags_and_positionals_with_positionals():
    """Mix of flags and positionals"""
    flags, positionals = separate_flags_and_positionals(
        ["-f", "app.exe", "--borderless"]
    )
    assert flags == [("-f", "app.exe"), ("--borderless", None)]
    assert positionals == []


@pytest.mark.unit
def test_separate_flags_and_positionals_only_flags():
    """Only flags, no positionals"""
    flags, positionals = separate_flags_and_positionals(["-W", "1920", "-H", "1080"])
    assert flags == [("-W", "1920"), ("-H", "1080")]
    assert positionals == []


@pytest.mark.unit
def test_separate_flags_and_positionals_only_positionals():
    """Only positionals, no flags"""
    flags, positionals = separate_flags_and_positionals(["app.exe", "arg1"])
    assert flags == []
    assert positionals == ["app.exe", "arg1"]


@pytest.mark.unit
def test_separate_flags_and_positionals_empty():
    """Empty input"""
    flags, positionals = separate_flags_and_positionals([])
    assert flags == []
    assert positionals == []


@pytest.mark.unit
def test_merge_arguments_basic():
    """Test basic argument merging"""
    result = merge_arguments(["-f"], ["--mangoapp"])
    assert "-f" in result
    assert "--mangoapp" in result


@pytest.mark.unit
def test_merge_arguments_conflict():
    """A different conflict flag in the override removes the profile's conflict."""
    # Profile has -f (fullscreen), override has --borderless (should win)
    result = merge_arguments(["-f", "-W", "1920"], ["--borderless"])
    assert "-f" not in result  # fullscreen removed
    assert "--borderless" in result  # borderless wins
    assert "-W" in result  # width preserved (not mutually exclusive)
    assert "1920" in result  # width value preserved


@pytest.mark.unit
def test_merge_arguments_width_override():
    """Test that width can be explicitly overridden"""
    # Profile has -W 1920, override explicitly sets different width
    result = merge_arguments(["-f", "-W", "1920"], ["--borderless", "-W", "2560"])
    assert "-f" not in result  # fullscreen removed due to conflict
    assert "--borderless" in result  # borderless wins
    assert "-W" in result  # width flag preserved
    assert "2560" in result  # new width value (overridden)
    assert "1920" not in result  # old width removed


@pytest.mark.unit
def test_merge_arguments_mutual_exclusivity():
    """Test that mutually exclusive flags are properly handled"""
    # Profile has -f (fullscreen), override has --borderless
    result = merge_arguments(["-f"], ["--borderless"])
    assert "-f" not in result  # -f should be replaced by --borderless
    assert "--borderless" in result

    # Override has -f, profile has --borderless
    result = merge_arguments(["--borderless"], ["-f"])
    assert "--borderless" not in result  # --borderless should be replaced by -f
    assert "-f" in result


@pytest.mark.unit
def test_merge_arguments_conflict_with_values():
    """Test conflict handling when flags have values"""
    # Profile has -W 1920, override has --borderless (should preserve width setting)
    result = merge_arguments(["-W", "1920"], ["--borderless"])
    assert "-W" in result  # Width flag should be preserved
    assert "1920" in result  # Width value should be preserved
    assert "--borderless" in result


@pytest.mark.unit
def test_merge_arguments_non_conflict_preservation():
    """Test that non-conflict flags are preserved when not overridden"""
    # Profile has -W 1920, override doesn't touch width (should be preserved)
    result = merge_arguments(["-f", "-W", "1920"], ["--borderless"])
    assert "-f" not in result  # fullscreen removed due to conflict
    assert "--borderless" in result  # borderless wins
    assert "-W" in result  # width preserved (not overridden)
    assert "1920" in result  # width value preserved


@pytest.mark.unit
def test_merge_multiple_profiles():
    """Test merging multiple profile argument lists"""
    # Test empty list
    assert merge_multiple_profiles([]) == []

    # Test single profile list (should return unchanged)
    assert merge_multiple_profiles([["-f", "-W", "1920"]]) == ["-f", "-W", "1920"]

    # Test multiple profiles with display mode conflicts
    profiles = [
        ["-f"],  # fullscreen
        ["--borderless"],  # should win over -f due to mutual exclusivity
        ["-W", "1920"],  # width setting that should be preserved
    ]
    result = merge_multiple_profiles(profiles)
    assert "--borderless" in result  # conflict winner
    assert "-f" not in result  # conflict loser removed
    assert "-W" in result  # non-conflict flag preserved

    # Test profiles with explicit width overrides
    profiles = [
        ["-f", "-W", "1920"],
        ["--borderless", "-W", "2560"],  # should override previous width setting
    ]
    result = merge_multiple_profiles(profiles)
    assert "--borderless" in result  # conflict winner
    assert "-f" not in result  # conflict loser removed
    assert "-W" in result  # width flag preserved
    assert "2560" in result  # latest value wins
    assert "1920" not in result  # old value removed


@pytest.mark.unit
def test_find_executable_true():
    """Test executable discovery when found"""
    with (
        patch.dict("os.environ", {"PATH": "/usr/bin:/bin"}),
        patch.object(Path, "exists", return_value=True),
        patch.object(Path, "is_dir", return_value=True),
        patch.object(Path, "is_file", return_value=True),
        patch("os.access", return_value=True),
    ):
        assert find_executable("gamescope") is True


@pytest.mark.unit
def test_find_executable_false():
    """Test executable discovery when not found"""
    with patch.dict("os.environ", {"PATH": ""}, clear=True):
        assert find_executable("gamescope") is False
