"""MCP Layer — AI-callable tools wrapping the retail domain engines.

These are *augmentation* tools, not the core engine: the AI orchestrator calls
them to run Huff/scoring/cannibalization/white-space analyses. Core business
logic always lives in the domain services they wrap.
"""
