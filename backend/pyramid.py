"""
DZI tile pyramid generator using PIL.
Generates a Deep Zoom Image pyramid compatible with OpenSeadragon.
"""

import math
from pathlib import Path


def generate_dzi(image_path: str, output_dir: str, tile_size: int = 256, overlap: int = 1) -> dict:
    """
    Generate a DZI tile pyramid from a large image.
    Returns image dimensions.
    """
    image_path = str(image_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    name = output_dir.name
    tiles_dir = output_dir.parent / (name + "_files")
    tiles_dir.mkdir(parents=True, exist_ok=True)

    # Load image with PIL for better PNG support with large files
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None  # allow huge images

    print(f"Loading {image_path} ...")
    img = Image.open(image_path)
    width, height = img.size
    print(f"  Size: {width}x{height}")

    # Convert to RGB if needed
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    # Calculate max level
    max_level = math.ceil(math.log2(max(width, height)))

    # Write .dzi descriptor
    dzi_path = output_dir.parent / (name + ".dzi")
    dzi_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<Image xmlns="http://schemas.microsoft.com/deepzoom/2008"
  Format="jpeg"
  Overlap="{overlap}"
  TileSize="{tile_size}">
  <Size Width="{width}" Height="{height}"/>
</Image>"""
    dzi_path.write_text(dzi_content)

    # Generate tiles level by level, from max down to 0
    current_img = img.copy()
    current_w, current_h = width, height

    for level in range(max_level, -1, -1):
        level_dir = tiles_dir / str(level)
        level_dir.mkdir(exist_ok=True)

        # Tile this level
        cols = math.ceil(current_w / tile_size)
        rows = math.ceil(current_h / tile_size)

        for row in range(rows):
            for col in range(cols):
                # Tile bounds with overlap
                x0 = col * tile_size - (overlap if col > 0 else 0)
                y0 = row * tile_size - (overlap if row > 0 else 0)
                x1 = min(x0 + tile_size + overlap * 2, current_w)
                y1 = min(y0 + tile_size + overlap * 2, current_h)
                x0 = max(0, x0)
                y0 = max(0, y0)

                tile = current_img.crop((x0, y0, x1, y1))
                tile_path = level_dir / f"{col}_{row}.jpeg"
                tile.save(str(tile_path), "JPEG", quality=85)

        # Downsample for next level
        if level > 0:
            new_w = max(1, current_w // 2)
            new_h = max(1, current_h // 2)
            current_img = current_img.resize((new_w, new_h), Image.LANCZOS)
            current_w, current_h = new_w, new_h

    print(f"  DZI written to {dzi_path}, {max_level+1} levels")
    return {"width": width, "height": height, "dzi_path": str(dzi_path)}
