"""
Utility: convert all images in ./images to .webp (in-place).
Handles .jpg, .jpeg, .png, .avif, .bmp, .tiff, etc.
Also reports which of the 100 cards (00-99) are missing images.
"""
from pathlib import Path
from PIL import Image

IMAGES_DIR = Path("images")
SUPPORTED = {".jpg", ".jpeg", ".png", ".avif", ".bmp", ".tiff", ".tif", ".gif"}


def convert_all():
    converted, skipped, failed = [], [], []

    for src in sorted(IMAGES_DIR.iterdir()):
        if src.suffix.lower() == ".webp":
            continue
        if src.suffix.lower() not in SUPPORTED:
            continue
        dst = src.with_suffix(".webp")
        try:
            Image.open(src).convert("RGBA").save(dst, "webp")
            src.unlink()
            converted.append(src.name)
            print(f"  ✓  {src.name}  →  {dst.name}")
        except Exception as e:
            failed.append(src.name)
            print(f"  ✗  {src.name}: {e}")

    # Report coverage
    missing = [f"{i:02d}" for i in range(100)
               if not (IMAGES_DIR / f"{i:02d}.webp").exists()]

    print(f"\nConverted: {len(converted)}  |  Skipped (already webp): {skipped}  |  Failed: {len(failed)}")
    if missing:
        print(f"Missing images ({len(missing)}): {', '.join(missing)}")
    else:
        print("All 100 cards have a .webp image.")


if __name__ == "__main__":
    convert_all()
