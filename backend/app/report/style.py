"""
PDF-only palette. The on-screen app is dark (pit-wall); the printable report is LIGHT — a sheet a
strategist marks up. The semantic colors (tyre compounds, the purple accent) carry over; only the
neutrals invert. Hex lives here (Python), never in the React components, so the frontend hex-grep
gate is unaffected.
"""

# neutrals (light print theme)
PAGE = "#FFFFFF"
INK = "#12161D"
MUTED = "#5B6472"
FAINT = "#8891A3"
HAIRLINE = "#D8DCE4"
CALLOUT_BG = "#F6F7F9"
AXIS = "#AEB6C2"

# semantic (kept from §4)
FASTEST = "#7E3FD6"  # brand purple, nudged darker for legible text on white
GAIN = "#0E9BB0"
LOSS = "#D8503C"

# tyre compounds — fill / on-chip text / outline (hard needs one on white)
COMPOUND: dict[str, dict[str, str]] = {
    "SOFT": {"fill": "#ED1C24", "text": "#FFFFFF", "stroke": "none", "letter": "S"},
    "MEDIUM": {"fill": "#FFD100", "text": "#12161D", "stroke": "none", "letter": "M"},
    "HARD": {"fill": "#F2F2F2", "text": "#12161D", "stroke": "#C7CCD6", "letter": "H"},
    "INTERMEDIATE": {"fill": "#00A651", "text": "#FFFFFF", "stroke": "none", "letter": "I"},
    "WET": {"fill": "#0072CE", "text": "#FFFFFF", "stroke": "none", "letter": "W"},
}
