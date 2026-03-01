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
from .version import __all__ as _version_all
from .server import __all__ as _server_all
from .api import __all__ as _api_all
from .timeouts import __all__ as _timeouts_all
from .models import __all__ as _models_all
from .errors import __all__ as _errors_all
from .limits import __all__ as _limits_all
from .sampling import __all__ as _sampling_all
from .streaming import __all__ as _streaming_all
from .thinking import __all__ as _thinking_all
from .security import __all__ as _security_all
from .images import __all__ as _images_all
from .mcp import __all__ as _mcp_all
from .selection import __all__ as _selection_all
from .testing import __all__ as _testing_all

__all__ = (
    _version_all + _server_all + _api_all + _timeouts_all + _models_all
    + _errors_all + _limits_all + _sampling_all + _streaming_all
    + _thinking_all + _security_all + _images_all + _mcp_all
    + _selection_all + _testing_all
)
