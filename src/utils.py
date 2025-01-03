"""Thermal Image Processing Utilities for MLX90641 Camera Module"""
import logging
from typing import List
import io
from PIL import Image
from viam.media.video import ViamImage

logger = logging.getLogger(__name__)

def create_heatmap_palette() -> List[int]:
    """Pre-compute and cache the heatmap palette"""
    palette: List[int] = []
    for i in range(256):
        if i < 85:  # Blue to Cyan
            palette.extend([0, 0, int(i * 3)])
        elif i < 170:  # Cyan to Yellow
            palette.extend([0, 255, 255 - int((i - 85) * 3)])
        else:  # Yellow to Red
            palette.extend([255, 255 - int((i - 170) * 3), 0])
    return palette


def create_thermal_image(
        frame: List[float],
        heatmap_palette: List[int],
        width: int,
        height: int) -> ViamImage:
    """
    Create a thermal image directly from sensor data.
    Combines normalization, heatmap application, and image creation into one optimized flow.
    """
    try:
        # Normalize temperatures to 0-255 range directly to bytes
        min_temp = min(frame)
        max_temp = max(frame)
        temp_range = max_temp - min_temp

        # Create normalized bytes directly
        normalized_data = bytes(
            int(255 * (temp - min_temp) / temp_range) if temp_range != 0 else 0
            for temp in frame
        )

        # Create image and apply transformations in one flow
        img = Image.frombytes('L', (32, 24), normalized_data).resize((width, height))

        # Apply heatmap palette
        img.putpalette(heatmap_palette)
        img = img.convert('RGB')

        # Convert to PNG with minimal compression
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG', optimize=False, compression_level=1)
        img_bytes.seek(0)
        return ViamImage(data=img_bytes.read(), mime_type='image/png')

    except Exception as e:
        logger.error("Failed to create thermal image %d:", e)
        raise
