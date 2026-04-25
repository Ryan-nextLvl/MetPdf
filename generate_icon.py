"""Generates assets/icon.ico for the UniversalPDF app."""

from pathlib import Path
from PIL import Image

def make_icon():
    assets = Path(__file__).parent / "assets"
    src = assets / "icon.png"
    out = assets / "icon.ico"

    sizes = [256, 128, 64, 48, 32, 16]
    base = Image.open(src).convert("RGBA")
    frames = [base.resize((s, s), Image.Resampling.LANCZOS) for s in sizes]

    frames[0].save(out, format="ICO", sizes=[(s, s) for s in sizes], append_images=frames[1:])
    print(f"Icon saved -> {out}")

if __name__ == "__main__":
    make_icon()
