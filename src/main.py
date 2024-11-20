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

def celsius_to_fahrenheit(celsius_temp) -> float:
    return (celsius_temp * 9/5) + 32

def convert_frame_to_fahrenheit(frame) -> List[float]:
    fahrenheit_frame = [celsius_to_fahrenheit(temp) for temp in frame]
    return fahrenheit_frame

    
## Implementation of the mlx90641 ir sensor
## This returns an arrya of temperatures
class MlxSensor(Sensor, EasyResource):
    MODEL: ClassVar[Model] = Model(
        ModelFamily("rand", "waveshare-thermal"), "mlx90641-ir-sensor"
    )
    mlx : adafruit_mlx90640.MLX90640
    _frame_buffer: List[float] = [0]*768
    # Add cache attributes
    _last_frame: Optional[List[float]] = None
    _last_reading_time: float = 0
    CACHE_DURATION = 0.1  # 100ms cache duration

    @classmethod
    def new(
      cls, config: ComponentConfig,
      dependencies: Mapping[ResourceName, ResourceBase]
      ) -> Self:
        mlxsensor = cls(config.name)

        # Initialize I2C bus
        i2c = busio.I2C(board.SCL, board.SDA)

        # Initialize the MLX90640 sensor
        mlx = adafruit_mlx90640.MLX90640(i2c)

        # Set the refresh rate
        mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_4_HZ
        
        mlxsensor.mlx = mlx
        
        # Create a frame buffer
        mlxsensor._frame_buffer = [0]*768 # MLX90640 has 768 pixels    

        return mlxsensor
    
    async def get_readings(
        self,
        *,
        extra: Optional[Mapping[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Mapping[str, SensorReading]:        
        try:
            # Read the thermal image
            self.mlx.getFrame(self._frame_buffer)
            frame = self._frame_buffer.copy()


        except Exception as e:
            raise  Exception(f"Error reading temperature: {e}")
        
        # give i2c some time to send over all the bytes, incase we have a high refresh
        # rate for a board/sensor combination
        time.sleep(1)
        
        readings_fahrenheit = convert_frame_to_fahrenheit(frame)
        
        return {
            "all_temperatures_celsius": frame,
            "min_temp_celsius" : min(frame),
            "max_temp_celsius" : max(frame),
            "all_temperatures_fahrenheit" : readings_fahrenheit,
            "min_temp_fahrenheit" : min(readings_fahrenheit),
            "max_temp_fahrenheit" : max(readings_fahrenheit),
        }

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
    img.save(img_bytes, format='PNG', optimize=False, compression_level=1)
    img_bytes.seek(0)
    
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
    heatmap_palette: List[int]

    @classmethod
    def new(
      cls, config: ComponentConfig,
      dependencies: Mapping[ResourceName, ResourceBase]
      ) -> Self:
        sensor_name = config.attributes.fields["sensor"].string_value
        if sensor_name == "":
            raise Exception("An mlx90641-ir-sensor attribute is required for an mlx90641-ir-camera.")
        
        sensor = dependencies[Sensor.get_resource_name(sensor_name)]
        mlxcamera = cls(config.name)
        mlxcamera.mlxsensor = cast(Sensor, sensor)
        mlxcamera.heatmap_palette = create_heatmap_palette()
        return mlxcamera
    
    @classmethod
    def validate(cls, config: ComponentConfig):
        sensor_name = config.attributes.fields["sensor"].string_value
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
        readings = await self.mlxsensor.get_readings()
        celcius = readings["all_temperatures_celsius"]
        return create_thermal_image(
            celcius,
            self.heatmap_palette, 
            width=240, 
            height=320
        )

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

