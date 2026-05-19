#!/usr/bin/env python
"""
Reference runner for Porter's response packaging scenarios.
Reuses the set-cover model from run-competitor-map.py — same template, different domain.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "run_competitor_map",
    Path(__file__).parent / "run-competitor-map.py",
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

if __name__ == "__main__":
    mod.main()
