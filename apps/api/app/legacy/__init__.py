"""Legacy modules for backward compatibility.

These modules are deprecated and will be removed in future versions.
They are kept here for backward compatibility with existing tests and code.

⚠️ WARNING: Do not use these modules in new code.
Use the new implementations in app.core instead.

Deprecated modules:
- rag_service_deprecated: Use app.services.multimodal_search_service instead
"""

import warnings

warnings.warn(
    "Legacy modules are deprecated and will be removed in future versions. "
    "Use new implementations in app.core instead.",
    DeprecationWarning,
    stacklevel=2,
)
