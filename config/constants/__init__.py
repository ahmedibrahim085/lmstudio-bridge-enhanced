"""Configuration constants — re-exports all domain modules for backward compatibility.

Usage unchanged:
    from config.constants import DEFAULT_LMSTUDIO_HOST  # still works
    from config.constants.server import DEFAULT_LMSTUDIO_HOST  # also works
"""

from .api import *
from .api import __all__ as _api_all
from .errors import *
from .errors import __all__ as _errors_all
from .images import *
from .images import __all__ as _images_all
from .limits import *
from .limits import __all__ as _limits_all
from .mcp import *
from .mcp import __all__ as _mcp_all
from .models import *
from .models import __all__ as _models_all
from .sampling import *
from .sampling import __all__ as _sampling_all
from .security import *
from .security import __all__ as _security_all
from .selection import *
from .selection import __all__ as _selection_all
from .server import *
from .server import __all__ as _server_all
from .streaming import *
from .streaming import __all__ as _streaming_all
from .testing import *
from .testing import __all__ as _testing_all
from .thinking import *
from .thinking import __all__ as _thinking_all
from .timeouts import *
from .timeouts import __all__ as _timeouts_all
from .tool_config import *
from .tool_config import __all__ as _tool_config_all
from .version import *

# Build package-level __all__ from all domain modules
from .version import __all__ as _version_all

__all__ = (
    _version_all + _server_all + _api_all + _timeouts_all + _models_all
    + _errors_all + _limits_all + _sampling_all + _streaming_all
    + _thinking_all + _security_all + _images_all + _mcp_all
    + _selection_all + _testing_all + _tool_config_all
)
