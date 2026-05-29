"""Simplified perpetual pair definitions."""

PAIRS = {
    "US/USDC": {
        "id": "US/USDC",
        "label": "US / USDC",
        "origin": "US",
        "description": "ICE Cotton No. 2 anchor (US origin index)",
        "anchor": "ICE",
    },
    "BRAZIL/USDC": {
        "id": "BRAZIL/USDC",
        "label": "Brazil / USDC",
        "origin": "BRAZIL",
        "description": "ICE anchor + structural Brazil basis + book EMA",
        "anchor": "ICE",
    },
    "AUSTRALIA/USDC": {
        "id": "AUSTRALIA/USDC",
        "label": "Australia / USDC",
        "origin": "AUSTRALIA",
        "description": "ICE anchor + structural Australia basis + book EMA",
        "anchor": "ICE",
    },
}

DEFAULT_PAIR = "US/USDC"
