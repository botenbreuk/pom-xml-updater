#!/usr/bin/env python3
"""Convert assets/app_icon_clean.png to platform-specific icon formats."""
import io
import struct
import sys
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
    icon_types = [
        ("icp4", 16),
        ("icp5", 32),
        ("icp6", 64),
        ("ic07", 128),
        ("ic08", 256),
        ("ic09", 512),
        ("ic10", 1024),
    ]

    entries = []
    for type_code, size in icon_types:
        buf = io.BytesIO()
        resized(size).save(buf, format="PNG")
        entries.append((type_code.encode("ascii"), buf.getvalue()))

    body = b""
    for type_code, png_bytes in entries:
        entry_length = 8 + len(png_bytes)
        body += type_code + struct.pack(">I", entry_length) + png_bytes

    total_length = 8 + len(body)
    output_path.write_bytes(b"icns" + struct.pack(">I", total_length) + body)
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
