"""Import shim for the hyphenated ``jit-context.py`` script."""

from __future__ import annotations

import importlib.util
from pathlib import Path


_SOURCE_PATH = Path(__file__).with_name("jit-context.py")
_SPEC = importlib.util.spec_from_file_location("attention_repo_jit_context", _SOURCE_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Unable to load module from {_SOURCE_PATH}")

_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

for _name in dir(_MODULE):
    if _name.startswith("__") and _name not in {"__doc__", "__all__"}:
        continue
    globals()[_name] = getattr(_MODULE, _name)

__all__ = getattr(_MODULE, "__all__", [name for name in globals() if not name.startswith("_")])
