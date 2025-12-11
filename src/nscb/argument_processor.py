"""Argument parsing and manipulation functionality for NeoscopeBuddy."""

from .types import ArgsList, FlagTuple, SeparatedArgs, SplitResult


class ArgumentProcessor:
    """Handles argument parsing and manipulation."""

    @staticmethod
    def split_at_separator(args: ArgsList) -> SplitResult:
        """Split arguments at '--' separator."""
        if "--" in args:
            idx = args.index("--")
            return args[:idx], args[idx:]
        return args, []

    @staticmethod
    def separate_flags_and_positionals(
        args: ArgsList,
    ) -> SeparatedArgs:
        """
        Split arguments into (flags, positionals).

        * `flags` – list of tuples ``(flag, value)`` where *value* is the
          following argument if it does **not** start with a dash; otherwise
          ``None``.  Flags are returned unchanged (short or long form).
        * `positionals` – arguments that do not begin with a dash.
        """
        flags: list[FlagTuple] = []
        positionals: ArgsList = []

        i = 0
        while i < len(args):
            arg = args[i]

            # Positional argument – keep as-is.
            if not arg.startswith("-"):
                positionals.append(arg)
                i += 1
                continue

            # Flag that may or may not have an accompanying value.
            if i + 1 < len(args) and not args[i + 1].startswith("-"):
                flags.append((arg, args[i + 1]))
                i += 2
            else:
                flags.append((arg, None))
                i += 1

        return flags, positionals
