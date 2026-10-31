"""Conservative preliminary safeguard for explicit Cognitive Memory writes.

Not a complete DLP system. The caller must still assess sensitivity and policy.
"""
from __future__ import annotations

import re

_SECRET_VALUE = re.compile(r"(?i)\b(?:sk-|sf-)[A-Za-z0-9_-]{12,}\b")
_SECRET_LABEL = re.compile(
    r"(?i)\b(?:senha|password|passphrase|api[\s_-]*key|chave[\s_-]*api|"
    r"access[\s_-]*token|refresh[\s_-]*token|secret[\s_-]*key|"
    r"credenciais?|bearer)\b"
)


def looks_like_credential(content: str) -> bool:
    """Reject likely credential text instead of sending it to cognitive storage."""
    return bool(_SECRET_VALUE.search(content) or _SECRET_LABEL.search(content))
