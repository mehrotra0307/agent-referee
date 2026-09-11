"""One-off generator for docs/assets/demo.gif.

Renders the real, verified output of `referee demo` as a terminal-style
animated GIF using Pillow, frame by frame. This exists because the repo's
docs/assets/demo.tape (a vhs script) needs a real headless browser to
render, which isn't available in every environment — this script has no
such dependency beyond Pillow (`pip install pillow`) and a system
monospace font. FONT_PATH below points at macOS's SF Mono; swap it for
any monospace .ttf path on other platforms.

Run from anywhere: python3 docs/assets/generate_demo_gif.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUTPUT_PATH = Path(__file__).parent / "demo.gif"
WIDTH, HEIGHT = 900, 720
BG = (13, 16, 13)
BAR_BG = (22, 27, 22)
INK = (223, 227, 219)
MUTED = (124, 154, 124)
GREEN = (110, 220, 140)
RED = (240, 120, 120)
AMBER = (227, 168, 62)
FONT_PATH = "/System/Library/Fonts/SFNSMono.ttf"
FONT_SIZE = 16
LINE_HEIGHT = 24
PADDING_X = 28
PADDING_TOP = 56

font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
font_bold = font

# Each line: (text, color). "" renders as a blank line (spacing only).
LINES = [
    ("$ referee demo", AMBER),
    ("", None),
    ("Agent Referee demo — no config file, no API key, nothing installed", MUTED),
    ("beyond this package. This wraps a tiny built-in mock agent so you can", MUTED),
    ("see the full loop before touching your own agent.", MUTED),
    ("", None),
    ("1. A normal question passes straight through, guardrails and tracing", INK),
    ("   running silently:", INK),
    ("", None),
    ("  · input_guardrail (0.2ms) — guardrail.allowed=True", MUTED),
    ("  · agent_call (0.0ms)", MUTED),
    ("  · output_guardrail (0.0ms) — guardrail.allowed=True", MUTED),
    ("   > We're open 11 AM to 11 PM, every day.", INK),
    ("", None),
    ("2. A message containing PII gets caught by the input guardrail", INK),
    ("   BEFORE the agent ever runs:", INK),
    ("", None),
    ("  · input_guardrail (0.0ms) — guardrail.allowed=False", RED),
    ("   > I can't help with that. (Blocked: message looks like a phone", RED),
    ("     number.)", RED),
    ("", None),
    ("3. A tiny evaluation, scoring the agent's real answer:", INK),
    ("", None),
    ("   [PASS] Looked for any of ['11 AM', '11 PM'] — found one.", GREEN),
    ("", None),
    ("Next: run `referee init` to wire this into your real agent.", MUTED),
]


def draw_frame(num_visible_lines, cursor_on=False):
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, WIDTH, 44], fill=BAR_BG)
    for i, color in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        cx = 26 + i * 24
        draw.ellipse([cx - 7, 22 - 7, cx + 7, 22 + 7], fill=color)

    y = PADDING_TOP
    for text, color in LINES[:num_visible_lines]:
        if color is not None:
            draw.text((PADDING_X, y), text, font=font, fill=color)
        y += LINE_HEIGHT

    if cursor_on and num_visible_lines < len(LINES):
        draw.rectangle([PADDING_X, y, PADDING_X + 10, y + FONT_SIZE + 2], fill=INK)

    return img


frames = []
durations = []

# Hold on just the command line for a beat, with a blinking cursor.
for blink in range(4):
    frames.append(draw_frame(1, cursor_on=(blink % 2 == 0)))
    durations.append(220)

# Reveal the rest of the output progressively.
for n in range(2, len(LINES) + 1):
    frames.append(draw_frame(n))
    durations.append(70)

# Hold on the finished frame at the end before looping.
for _ in range(3):
    frames.append(draw_frame(len(LINES)))
    durations.append(1400)

frames[0].save(
    OUTPUT_PATH,
    save_all=True,
    append_images=frames[1:],
    duration=durations,
    loop=0,
    optimize=True,
)
print(f"Wrote {OUTPUT_PATH} ({len(frames)} frames)")
