"""Configuration constants — re-exports all domain modules for backward compatibility.

Usage unchanged:
    from config.constants import DEFAULT_LMSTUDIO_HOST  # still works
    from config.constants.server import DEFAULT_LMSTUDIO_HOST  # also works
"""

from .version import *
from .server import *
from .api import *
from .timeouts import *
from .models import *
from .errors import *
from .limits import *
from .sampling import *
from .streaming import *
from .thinking import *
from .security import *
from .images import *
from .mcp import *
from .selection import *
from .testing import *

# Build package-level __all__ from all domain modules
from . import (
    version, server, api, timeouts, models, errors, limits,
    sampling, streaming, thinking, security, images, mcp,
    selection, testing,
)

__all__: list[str] = []
for _mod in (
    version, server, api, timeouts, models, errors, limits,
    sampling, streaming, thinking, security, images, mcp,
    selection, testing,
):
    __all__.extend(getattr(_mod, "__all__", []))
del _mod
