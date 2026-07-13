#!/usr/bin/env python3
"""Convert assets/app_icon_clean.png to platform-specific icon formats."""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Missing dependency. Install with: pip install Pillow")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).parent.parent
SOURCE_PNG   = PROJECT_ROOT / "assets" / "app_icon_clean.png"
OUTPUT_DIR   = Path(__file__).parent / "icons"


def resized(size: int) -> Image.Image:
    img = Image.open(SOURCE_PNG).convert("RGBA")
    return img.resize((size, size), Image.LANCZOS)


def create_ico(output_path: Path) -> None:
    sizes = [16, 24, 32, 48, 64, 128, 256]
    resized(256).save(output_path, format="ICO", sizes=[(s, s) for s in sizes])
    print(f"Created {output_path} ({output_path.stat().st_size:,} bytes)")


def create_icns(output_path: Path) -> None:
    if shutil.which("iconutil") is None:
        print("Error: iconutil not found. Building .icns requires macOS.")
        sys.exit(1)

    # Standard Apple iconset naming: (size, filename).
    names = [
        (16, "icon_16x16.png"),
        (32, "icon_16x16@2x.png"),
        (32, "icon_32x32.png"),
        (64, "icon_32x32@2x.png"),
        (128, "icon_128x128.png"),
        (256, "icon_128x128@2x.png"),
        (256, "icon_256x256.png"),
        (512, "icon_256x256@2x.png"),
        (512, "icon_512x512.png"),
        (1024, "icon_512x512@2x.png"),
    ]

    with tempfile.TemporaryDirectory() as tmp:
        iconset_dir = Path(tmp) / "icon.iconset"
        iconset_dir.mkdir()
        for size, name in names:
            resized(size).save(iconset_dir / name)

        subprocess.run(
            ["iconutil", "-c", "icns", "-o", str(output_path), str(iconset_dir)],
            check=True,
        )
    print(f"Created {output_path} ({output_path.stat().st_size:,} bytes)")


def create_png(output_path: Path) -> None:
    resized(1024).save(output_path, format="PNG")
    print(f"Created {output_path} ({output_path.stat().st_size:,} bytes)")


def main():
    if not SOURCE_PNG.exists():
        print(f"Error: {SOURCE_PNG} not found")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Converting {SOURCE_PNG}...")
    create_ico(OUTPUT_DIR / "icon.ico")
    create_icns(OUTPUT_DIR / "icon.icns")
    create_png(OUTPUT_DIR / "icon.png")
    print("Done!")


if __name__ == "__main__":
    main()
