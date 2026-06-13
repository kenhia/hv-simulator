"""Smoke test: the package imports and the toolchain runs.

Replaced/expanded by real tests starting in Sprint 002.
"""

import hvsim


def test_package_imports():
    assert hvsim.__version__ == "0.1.0"
