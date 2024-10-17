#!/usr/bin/env python3
import asyncio
from typing import (Any, ClassVar, Dict, List, Mapping, Optional, cast, Tuple)


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
        sensor_name = attributes_dict("sensor", "")
        if sensor_name == "":
            raise Exception("An mlx90641-ir-sensor attribute is required for an mlx90641-ir-camera.")
        
        sensor = dependencies[Sensor.get_resource_name(sensor_name)]
        mlxcamera = cls(config.name)
        # mlxcamera.mlxsensor = cast(Sensor, sensor)
        return mlxcamera
    
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

