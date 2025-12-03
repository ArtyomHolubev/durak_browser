import os
from pathlib import Path

RANKS = ["6", "7", "8", "9", "10", "J", "Q", "K", "A"]
SUITS = {
    "C": "♣",
    "D": "♦",
    "H": "♥",
    "S": "♠",
}
COLORS = {"C": "#111", "S": "#111", "D": "#c62121", "H": "#c62121"}
OUTPUT_DIR = Path("public/cards")

SVG_TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" width="140" height="200" viewBox="0 0 140 200">
  <rect x="4" y="4" width="132" height="192" rx="16" ry="16" fill="#fff" stroke="#1d2333" stroke-width="4"/>
  <text x="16" y="32" font-family="'Segoe UI', sans-serif" font-size="26" fill="{color}" font-weight="600">{rank}</text>
  <text x="20" y="58" font-family="'Segoe UI', sans-serif" font-size="28" fill="{color}">{symbol}</text>
  <g transform="rotate(180 70 100)">
    <text x="16" y="32" font-family="'Segoe UI', sans-serif" font-size="26" fill="{color}" font-weight="600">{rank}</text>
    <text x="20" y="58" font-family="'Segoe UI', sans-serif" font-size="28" fill="{color}">{symbol}</text>
  </g>
  <text x="70" y="110" text-anchor="middle" font-family="'Segoe UI', sans-serif" font-size="72" fill="{color}" font-weight="600">{symbol}</text>
</svg>
"""


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for suit, symbol in SUITS.items():
        color = COLORS[suit]
        for rank in RANKS:
            name = f"{rank}{suit}"
            svg = SVG_TEMPLATE.format(color=color, rank=rank, symbol=symbol)
            (OUTPUT_DIR / f"{name}.svg").write_text(svg, encoding="utf-8")
    print("Generated 36 SVG cards in", OUTPUT_DIR)


if __name__ == "__main__":
    main()
