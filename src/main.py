#!/usr/bin/env python3
import asyncio
from typing import (Any, ClassVar, Dict, List, Mapping, Optional, cast, Tuple)
import io

from typing_extensions import Self
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
from PIL import Image

import board
import busio
import adafruit_mlx90640
import time

def celsius_to_fahrenheit(celsius_temp):
    return (celsius_temp * 9/5) + 32

def convert_frame_to_fahrenheit(frame):
    fahrenheit_frame = [celsius_to_fahrenheit(temp) for temp in frame]
    return fahrenheit_frame

    
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
        try:

            # Initialize I2C bus
            i2c = busio.I2C(board.SCL, board.SDA)

        # Initialize the MLX90640 sensor
            mlx = adafruit_mlx90640.MLX90640(i2c)

        # Set the refresh rate
            mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_0_5_HZ

            # Create a frame buffer
            readings = [0] * 768  # MLX90640 has 768 pixels    
            # Read the thermal image
            mlx.getFrame(readings)

        # # Print temperatures for each pixel
        #     for i in range(0, 192):  # 192 pixels in a 32x24 array
        #         print(f"Pixel {i}: {frame[i]:.2f} °C")

        except Exception as e:
            raise  Exception(f"Error reading temperature: {e}")
        
        # give i2c some time to send over all the bytes, incase we have a high refresh
        # rate for a board/sensor combination
        time.sleep(1)
        
        readings_fahrenheit = convert_frame_to_fahrenheit(readings)
        
        return {
            "all_temperatures_celcius": readings,
            "min_temp_celcius" : min(readings),
            "max_temp_celsius" : max(readings),
            "all_temperatures_fahrenheit" : readings_fahrenheit,
            "min_temp_fahrenheit" : min(readings_fahrenheit),
            "max_temp_fahrenheit" : max(readings_fahrenheit),
        }


# Normalize frame data to 0-255 for grayscale
def normalize_frame(frame):
    min_temp = min(frame)
    max_temp = max(frame)
    normalized_frame = [
        int(255 * (value - min_temp) / (max_temp - min_temp)) for value in frame
    ]
    return normalized_frame


# Nearest-neighbor resize function
def resize_image(data_2d, new_width, new_height):
    original_height = len(data_2d)
    original_width = len(data_2d[0])
    
    # Create a new 2D array for the resized image
    resized_image = [[0] * new_width for _ in range(new_height)]
    
    for new_row in range(new_height):
        for new_col in range(new_width):
            # Find the corresponding position in the original image
            old_row = int(new_row * original_height / new_height)
            old_col = int(new_col * original_width / new_width)
            
            # Assign the pixel value from the original image
            resized_image

# Create a ViamImage from the normalized frame with resizing
def create_viam_image(normalized_frame, new_width, new_height) -> ViamImage:
    # Reshape the 1D frame into a 32x24 2D array
    image_data = []
    for row in range(24):
        start_index = row * 32
        end_index = start_index + 32
        image_data.append(normalized_frame[start_index:end_index])

    # Flatten the 2D array into a single list of pixel values
    flat_image_data = [pixel for row in image_data for pixel in row]

    # Convert the list of pixel values into bytes
    byte_data = bytes(flat_image_data)

    # Create a Pillow image from the bytes (32x24 grayscale)
    img = Image.frombytes('L', (32, 24), byte_data)

    # Resize the image using Pillow
    img_resized = img.resize((new_width, new_height), Image.NEAREST)

    # Convert the resized image to a PNG byte stream
    img_bytes = io.BytesIO()
    img_resized.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    # Return the ViamImage with the resized image data as bytes
    return ViamImage(data=img_bytes.read(), mime_type='image/png')

## Implementation of the Mlx90641 Camera
## this uses the sensor to create an resized image so you can see 
## the thermal image it is producing
## The image is not appropriate for use in trainign models
class MlxCamera(Camera, EasyResource):
    MODEL: ClassVar[Model] = Model(
        ModelFamily("rand", "waveshare-thermal"), "mlx90641-ir-camera"
    )
    mlxsensor : Sensor

    @classmethod
    def new(
      cls, config: ComponentConfig,
      dependencies: Mapping[ResourceName, ResourceBase]
      ) -> Self:
        attributes_dict = struct_to_dict(config.attributes)
        sensor_name = attributes_dict.get("sensor")
        assert isinstance(sensor_name, str) 
        if sensor_name == "":
            raise Exception("An mlx90641-ir-sensor attribute is required for an mlx90641-ir-camera.")
        
        
        mlxcamera = cls(config.name)
        print("\n\n deps ", dependencies)
        print("sensorname: ",  sensor_name, "\n\n")
        mlxcamera.mlxsensor = dependencies[Sensor.get_resource_name(sensor_name)]
        return mlxcamera

    async def get_image(
        self,
        mime_type: str = "",
        *,
        extra: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> ViamImage:
        readings = await self.mlxsensor.get_readings()
        frame = readings["all_temperatures_celcius"]

        # Normalize frame for grayscale conversion
        normalized_frame = normalize_frame(frame)

        # Create and return the resized ViamImage
        return create_viam_image(normalized_frame, 240, 320)

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
            return Camera.Properties(
                mime_types=['image/png'],
                supports_pcd= False           
    )

if __name__ == "__main__":
    asyncio.run(Module.run_from_registry())

