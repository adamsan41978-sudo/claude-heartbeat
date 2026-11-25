import pytest
from PIL import ImageColor

from claude_heartbeat.icons import COLORS, make_icon
from claude_heartbeat.state import State


@pytest.mark.parametrize("state", list(State))
def test_icon_shape(state):
    img = make_icon(state, 64)
    assert img.size == (64, 64) and img.mode == "RGBA"
    assert img.getpixel((0, 0))[3] == 0  # rounded corner is transparent


def _pixels(state, rgb):
    img = make_icon(state, 64)
    return [(x, y) for y in range(64) for x in range(64) if img.getpixel((x, y))[:3] == rgb]


def test_awake_is_green_watching_is_not():
    green = ImageColor.getrgb(COLORS[State.AWAKE])
    assert _pixels(State.AWAKE, green)
    assert not _pixels(State.WATCHING, green)


def test_off_glyph_is_flat():
    rows = {y for _, y in _pixels(State.OFF, ImageColor.getrgb(COLORS[State.OFF]))}
    assert rows and max(rows) - min(rows) <= 64 // 9 + 1
