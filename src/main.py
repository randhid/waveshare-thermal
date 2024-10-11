import asyncio
import sys
from typing import (Any, ClassVar, Dict, Final, List, Mapping, Optional,
                    Sequence, Tuple)

from typing_extensions import Self
from viam.components.camera import Camera
from viam.media.video import NamedImage, ViamImage
from viam.module.module import Module
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import ResourceName, ResponseMetadata
from viam.proto.component.camera import GetPropertiesResponse
from viam.resource.base import ResourceBase
from viam.resource.easy_resource import EasyResource
from viam.resource.types import Model, ModelFamily


import os
import fcntl
import struct

I2C_SLAVE = 0x0703
MLX90640_I2C_ADDR = 0x33  # Default I2C address for MLX90640
I2C_DEVICE = "/dev/i2c-1"  # Default I2C bus for Raspberry Pi

# Open the I2C device
def open_i2c_device():
    fd = os.open(I2C_DEVICE, os.O_RDWR)
    fcntl.ioctl(fd, I2C_SLAVE, MLX90640_I2C_ADDR)
    return fd

# Read raw data from the MLX90640 sensor
def read_sensor_data(fd):
    # Assuming the sensor returns 768 readings, each 16 bits
    raw_data = os.read(fd, 1536)  # 768 * 2 bytes
    return raw_data

# Convert raw bytes to frame data (temperature readings)
def parse_frame(raw_data):
    frame = []
    for i in range(0, len(raw_data), 2):
        # Convert two bytes into one 16-bit integer
        val = struct.unpack('<H', raw_data[i:i+2])[0]
        frame.append(val)
    return frame

# Normalize frame data to 0-255 for grayscale
def normalize_frame(frame):
    min_temp = min(frame)
    max_temp = max(frame)
    normalized_frame = [
        int(255 * (value - min_temp) / (max_temp - min_temp)) for value in frame
    ]
    return normalized_frame

# Create a ViamImage from the normalized frame
def create_viam_image(normalized_frame) -> ViamImage:
    # Reshape the 1D frame into a 32x24 2D array
    image_data = []
    for row in range(24):
        start_index = row * 32
        end_index = start_index + 32
        image_data.append(normalized_frame[start_index:end_index])

    # Create and return the ViamImage (assuming grayscale PNG is expected)
    return ViamImage(data=image_data, mime_type='image/png')

# Main logic to capture the image
def capture_thermal_image() -> ViamImage:
    try:
        fd = open_i2c_device()

        # Read raw sensor data
        raw_data = read_sensor_data(fd)

        # Parse raw data into temperature frame
        frame = parse_frame(raw_data)

        # Normalize frame for grayscale conversion
        normalized_frame = normalize_frame(frame)

        # Create and return the ViamImage
        return create_viam_image(normalized_frame)
    
    finally:
        # Close the I2C device
        os.close(fd)

# # Example usage
# viam_image = capture_thermal_image()
# print("ViamImage created successfully.")


class Mlx90641Ir(Camera, EasyResource):
    MODEL: ClassVar[Model] = Model(
        ModelFamily("rand", "waveshare-thermal"), "mlx90641-ir"
    )

    @classmethod
    def new(
        cls, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]
    ) -> Self:
        return 

    @classmethod
    def validate_config(cls, config: ComponentConfig) -> Sequence[str]:
        return []

    def reconfigure(
        self, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]
    ):
        return super().reconfigure(config, dependencies)

    async def get_image(
        self,
        mime_type: str = "",
        *,
        extra: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> ViamImage:
        image = capture_thermal_image()
        return image

    async def get_images(
        self, *, timeout: Optional[float] = None, **kwargs
    ) -> Tuple[
        List[NamedImage], ResponseMetadata
    ]:
        raise NotImplementedError()

    async def get_point_cloud(
        self,
        *,
        extra: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Tuple[bytes, str]:
        raise NotImplementedError()

    async def get_properties(
        self, *, timeout: Optional[float] = None, **kwargs
    ) -> GetPropertiesResponse:
        raise NotImplementedError()


if __name__ == "__main__":
    asyncio.run(Module.run_from_registry())

