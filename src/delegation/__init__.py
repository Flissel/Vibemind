"""Delegation orchestration package.

This package provides entrypoints and utilities to run multi-step plans that
call existing plugins via the PluginManager. It also offers an optional
integration scaffold with AutoGen if installed, with a safe fallback to a
lightweight in-process planner.
"""