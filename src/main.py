#!/usr/bin/env python3
import asyncio
import os
import fcntl
import struct
from typing import (Any, ClassVar, Dict, List, Mapping, Optional, cast, Tuple)


# from typing_extensions import Self
from viam.components.camera import Camera 
from viam.components.sensor import Sensor
from viam.module.module import Module
from viam.media.video import ViamImage, NamedImage
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import ResponseMetadata, ResourceName
from viam.proto.component.camera import GetPropertiesResponse
from viam.resource.base import ResourceBase
from viam.resource.easy_resource import EasyResource
from viam.resource.types import Model, ModelFamily
from viam.utils import SensorReading, struct_to_dict



I2C_TARGET = 0x0703
MLX90640_I2C_ADDR = 0x33  # Default I2C address for MLX90640
I2C_DEVICE = "/dev/i2c-1"  # Default I2C bus for Raspberry Pi

# Open the I2C device
def open_i2c_device():
    fd = os.open(I2C_DEVICE, os.O_RDWR)
    fcntl.ioctl(fd, I2C_TARGET, MLX90640_I2C_ADDR)
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
        val = struct.unpack('<h', raw_data[i:i+2])[0]
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

# Nearest-neighbor interpolation for resizing
def resize_image(image_data, new_width, new_height):
    old_height = len(image_data)
    old_width = len(image_data[0])

    # Create the resized image placeholder
    resized_image = [[0 for _ in range(new_width)] for _ in range(new_height)]

    # Calculate scale factors
    x_ratio = old_width / new_width
    y_ratio = old_height / new_height

    for new_y in range(new_height):
        for new_x in range(new_width):
            # Find the nearest pixel in the original image
            old_x = int(new_x * x_ratio)
            old_y = int(new_y * y_ratio)

            # Assign the pixel to the new image
            resized_image[new_y][new_x] = image_data[old_y][old_x]

    return resized_image

# Create a ViamImage from the normalized frame
def create_viam_image(normalized_frame) -> ViamImage:
    # Reshape the 1D frame into a 32x24 2D array
    image_data = []
    for row in range(24):
        start_index = row * 32
        end_index = start_index + 32
        image_data.append(normalized_frame[start_index:end_index])

    # Resize the image to 120x160 using nearest-neighbor interpolation
    resized_image_data = resize_image(image_data, 120, 160)

    # Create and return the ViamImage (assuming grayscale PNG is expected)
    return ViamImage(data=resized_image_data, mime_type='image/png')
    
# Main logic to get frames
def capture_thermal_data() -> List:
    try:
        fd = open_i2c_device()

        # Read raw sensor data
        raw_data = read_sensor_data(fd)

        # Create and return the resized ViamImage
        return parse_frame(raw_data)
    
    finally:
        # Close the I2C device
        os.close(fd)

## Implementation of the mlx90641 ir sensor
## This returns an arrya of temperatures
class MlxSensor(Sensor, EasyResource):
    MODEL: ClassVar[Model] = Model(
        ModelFamily("rand", "waveshare-thermal"), "mlx90641-ir-sensor"
    )

    async def get_readings(
        self,
        *,
        extra: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Mapping[str, SensorReading]:
        readings = capture_thermal_data()

        return {
            "all_temperatures": readings,
            "min_temp_celcius" : min(readings),
            "max_temp_celsius" : max(readings)
        }


## Implementation of the Mlx90641 Camera
## this uses the sensor to create an resized image so you can see 
## the thermal image it is producing
## The image is not appropriate for use in trainign models
class MlxCamera(Camera, EasyResource):
    MODEL: ClassVar[Model] = Model(
        ModelFamily("rand", "waveshare-thermal"), "mlx90641-ir-camera"
    )
    # mlxsensor : Sensor

    # @classmethod
    # def new(
    #   cls, config: ComponentConfig,
    #   dependencies: Mapping[ResourceName, ResourceBase]
    #   ) -> Self:
    #     attributes_dict = struct_to_dict(config.attributes)
    #     sensor_name = attributes_dict("sensor", "")
    #     if sensor_name == "":
    #         raise Exception("An mlx90641-ir-sensor attribute is required for an mlx90641-ir-camera.")
        
    #     sensor = dependencies[Sensor.get_resource_name(sensor_name)]
    #     mlxcamera = cls(config.name)
    #     # mlxcamera.mlxsensor = cast(Sensor, sensor)
    #     return mlxcamera
    
    @classmethod
    def validate(cls, config: ComponentConfig):
        attributes_dict = struct_to_dict(config.attributes)
        sensor_name = attributes_dict.get("sensor", "")
        assert isinstance(sensor_name, str)
        if sensor_name == "":
            raise Exception("An mlx90641-ir-sensor attribute is required for an mlx90641-ir-camera.")
        return [sensor_name]

    async def get_image(
        self,
        mime_type: str = "",
        *,
        extra: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> ViamImage:
        # readings = await self.mlxsensor.get_readings()
        # frame = readings["all_temperatures"]

        # # Normalize frame for grayscale conversion
        # normalized_frame = normalize_frame(frame)

        # # Create and return the resized ViamImage
        # return create_viam_image(normalized_frame)
        raise NotImplementedError()

    async def get_images(
        self, *, timeout: Optional[float] = None, **kwargs
    ) -> Tuple[List[NamedImage], ResponseMetadata]:
        raise NotImplementedError()

    async def get_point_cloud(
        self, *, extra: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None, **kwargs
    ) -> Tuple[bytes, str]:
        raise NotImplementedError()

    async def get_properties(
        self, *, timeout: Optional[float] = None, **kwargs
    ) -> GetPropertiesResponse:
            raise NotImplementedError() 

if __name__ == "__main__":
    asyncio.run(Module.run_from_registry())

