#!/usr/bin/env python3
"""Fail if core pyiv imports third-party libraries.

Allowed exception: pyiv/serde/__init__.py may lazy-import pyiv_common for the
YAMLSerDe compatibility shim. It must not import yaml or requests.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

FORBIDDEN = frozenset({"yaml", "requests", "pyyaml"})
SHIM_REL = Path("pyiv/serde/__init__.py")


def imported_roots(node: ast.AST) -> set[str]:
    names: set[str] = set()
    if isinstance(node, ast.Import):
        for alias in node.names:
            names.add(alias.name.split(".", 1)[0])
    elif isinstance(node, ast.ImportFrom) and node.module:
        names.add(node.module.split(".", 1)[0])
    return names


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    root = repo / "pyiv"
    shim = (repo / SHIM_REL).resolve()
    errors: list[str] = []

    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        rel = path.relative_to(repo)
        for node in ast.walk(tree):
            for name in imported_roots(node):
                if name in FORBIDDEN:
                    errors.append(f"{rel}: imports {name}")
                if name == "pyiv_common" and path.resolve() != shim:
                    errors.append(
                        f"{rel}: imports pyiv_common " f"(shim is only allowed in {SHIM_REL})"
                    )

    if errors:
        print("Core pyiv must stay stdlib-only:")
        for line in errors:
            print(f"  {line}")
        return 1
    print("Core stdlib import guard passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
