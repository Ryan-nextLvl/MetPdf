"""Generates assets/icon.ico for the MetePDF app."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def make_icon():
    assets = Path(__file__).parent / "assets"
    assets.mkdir(exist_ok=True)
    out = assets / "icon.ico"

    sizes = [256, 128, 64, 48, 32, 16]
    frames = []

    for size in sizes:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Background rounded square
        pad = size // 12
        draw.rounded_rectangle([pad, pad, size - pad, size - pad],
                                radius=size // 6, fill="#1a6fc4")

        # White page shape
        pw = int(size * 0.44)
        ph = int(size * 0.56)
        px = (size - pw) // 2
        py = int(size * 0.18)
        fold = pw // 4

        # Page body
        draw.polygon([
            (px, py),
            (px + pw - fold, py),
            (px + pw, py + fold),
            (px + pw, py + ph),
            (px, py + ph),
        ], fill="white")

        # Fold triangle
        draw.polygon([
            (px + pw - fold, py),
            (px + pw - fold, py + fold),
            (px + pw, py + fold),
        ], fill="#a8c8f0")

        # PDF text
        font_size = max(8, size // 6)
        try:
            font = ImageFont.truetype("arialbd.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()

        text = "PDF"
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        tx = px + (pw - tw) // 2
        ty = py + ph - th - max(4, size // 16)
        draw.text((tx, ty), text, fill="#1a6fc4", font=font)

        frames.append(img)

    frames[0].save(out, format="ICO", sizes=[(s, s) for s in sizes], append_images=frames[1:])
    print(f"Icon saved -> {out}")

if __name__ == "__main__":
    make_icon()
