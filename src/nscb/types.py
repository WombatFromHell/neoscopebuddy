"""Type aliases for NeoscopeBuddy."""

from typing import Dict, List, Optional, Tuple

# Type aliases at the top of the file for readability
ArgsList = List[str]
FlagTuple = Tuple[str, Optional[str]]
ProfileArgs = Dict[str, str]
ConfigData = Dict[str, str]
EnvExports = Dict[str, str]
ExitCode = int
ProfileArgsList = List[ArgsList]
