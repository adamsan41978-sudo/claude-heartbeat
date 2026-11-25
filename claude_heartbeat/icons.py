"""Tray icons: a shared dark-navy tile (the "system tools" family frame) + a heartbeat glyph.

Future tools reuse TILE and the rounded frame, swapping the glyph and accent color.
Drawn without anti-aliasing so every pixel is an exact palette color.
"""
from PIL import Image, ImageDraw

from .state import State

TILE = "#14213D"
COLORS: dict[State, str] = {
    State.AWAKE: "#2EE59D",     # bright green: holding the PC awake
    State.WATCHING: "#5C7A99",  # dim grey-blue: armed, nothing to hold
    State.OFF: "#6B6B6B",       # grey flat line: switched off
}

_PULSE = [(0.12, 0.55), (0.35, 0.55), (0.45, 0.25), (0.55, 0.78), (0.63, 0.55), (0.88, 0.55)]
_FLAT = [(0.12, 0.55), (0.88, 0.55)]


def make_icon(state: State, size: int = 64) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=size // 5, fill=TILE)
    points = _FLAT if state is State.OFF else _PULSE
    draw.line(
        [(x * size, y * size) for x, y in points],
        fill=COLORS[state],
        width=max(2, size // 9),
        joint="curve",
    )
    return img
