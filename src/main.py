#!/usr/bin/env python3
"""MLX90641 IR Thermal Sensor and Camera Components."""

import asyncio
import os
import time
from threading import Event, Lock, Thread
from typing import Any, ClassVar, Dict, List, Mapping, Optional, Tuple, cast

import adafruit_mlx90640
import board
import busio
from typing_extensions import Self
from viam.components.camera import Camera
from viam.components.sensor import Sensor
from viam.media.video import NamedImage, ViamImage
from viam.module.module import Module
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import ResourceName, ResponseMetadata
from viam.proto.component.camera import GetPropertiesResponse
from viam.resource.base import ResourceBase
from viam.resource.easy_resource import EasyResource
from viam.resource.types import Model, ModelFamily
from viam.utils import SensorReading

import utils

REFRESH_RATE_MAP = {
    0.5: adafruit_mlx90640.RefreshRate.REFRESH_0_5_HZ,
    1: adafruit_mlx90640.RefreshRate.REFRESH_1_HZ,
    2: adafruit_mlx90640.RefreshRate.REFRESH_2_HZ,
    4: adafruit_mlx90640.RefreshRate.REFRESH_4_HZ,
    8: adafruit_mlx90640.RefreshRate.REFRESH_8_HZ,
    16: adafruit_mlx90640.RefreshRate.REFRESH_16_HZ,
    32: adafruit_mlx90640.RefreshRate.REFRESH_32_HZ,
    64: adafruit_mlx90640.RefreshRate.REFRESH_64_HZ,
}

## Implementation of the mlx90641 ir sensor
## This returns an arrya of temperatures
class MlxSensor(Sensor, EasyResource):
    """MLX90641 IR Sensor Component."""
    MODEL: ClassVar[Model] = Model(
        ModelFamily("rand", "waveshare-thermal"), "mlx90641-ir-sensor"
    )

    mlx : adafruit_mlx90640.MLX90640
    _frame_lock = Lock()
    _stop_event = Event()
    _read_thread: Optional[Thread] = None
    _frame_buffer: List[float] = [0]*768
    # Add cache attributes
    _last_frame: Optional[List[float]] = [0]*768
    _last_reading_time: float = 0
    CACHE_DURATION = 0.001  # 1ms cache duration
    MAX_RETRIES = 3
    BASE_DELAY = 0.05  # Base delay between retries in seconds

    @classmethod
    def new(
        cls,
        config: ComponentConfig,
        dependencies: Mapping[ResourceName, ResourceBase]) -> Self:
        """Create a new MLX90640 sensor instance."""
        mlxsensor = cls(config.name)
        mlxsensor.reconfigure(config, dependencies)
        return mlxsensor

    def _start_reading(self):
        if self._read_thread and self._read_thread.is_alive():
            self._stop_event.set()
            self._read_thread.join()
        self._stop_event.clear()
        self._read_thread = Thread(target=self._read_frame, daemon=True)
        self._read_thread.start()

    def _read_frame(self):
        retry_count = 0
        while not self._stop_event.is_set():
            try:
                for attempt in range(self.MAX_RETRIES):
                    try:
                        self.mlx.getFrame(self._frame_buffer)
                        with self._frame_lock:
                            self._last_frame = self._frame_buffer.copy()
                            self._last_reading_time = time.time()
                        break
                    except OSError as e:
                        if attempt == self.MAX_RETRIES - 1:
                            raise e
                        time.sleep(self.BASE_DELAY)
                retry_count = 0
            except Exception as e:
                retry_count += 1
                print(f"Frame error: {e} (retry {retry_count})")
                time.sleep(self.BASE_DELAY)

    def reconfigure(
            self,
            config: ComponentConfig,
            dependencies: Mapping[ResourceName, ResourceBase]):
        """Reconfigure the MLX90640 sensor."""
        # Check for I2C buses
        i2c_buses = [f"/dev/{file}" for file in os.listdir("/dev") if file.startswith("i2c-")]
        if not i2c_buses:
            raise Exception(
                "i2c not enabled on your device, we tried enabling it through modprobe" +
                "please ssh into your pi and enable it through sudo raspi-config")

        # Initialize I2C bus
        i2c = busio.I2C(board.SCL, board.SDA, frequency=1000000)

        # Initialize the MLX90640 sensor
        mlx = adafruit_mlx90640.MLX90640(i2c)
        time.sleep(0.1)  # Allow calibration to take effect

        # Set the refresh rate
        refresh_rate = config.attributes.fields["refresh_rate_hz"].number_value

        # Store refresh rate for delay calculations
        self.refresh_rate = refresh_rate

        # Set refresh rate with fallback
        try:
            mlx.refresh_rate = REFRESH_RATE_MAP.get(
                refresh_rate,
                adafruit_mlx90640.RefreshRate.REFRESH_4_HZ  # default fallback
            )
            time.sleep(0.1)  # Allow settings to take effect

        except KeyError:
            print(f"Invalid refresh rate {refresh_rate}Hz, using 4Hz")
            mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_4_HZ

        # Update instance variables
        self.mlx = mlx
        self._frame_buffer = [0]*768  # MLX90640 has 768 pixels

        self._start_reading()

    async def get_readings(
            self,
            *,
            extra: Optional[Mapping[str, Any]] = None,
            timeout: Optional[float] = None,
            **kwargs
        ) -> Mapping[str, SensorReading]:

            with self._frame_lock:
                frame = self._last_frame.copy()

            # Convert frame data to readings
            readings_celsius = frame
            readings_fahrenheit = [(temp * 9/5) + 32 for temp in readings_celsius]

            # Convert 1D to 2D (24x32), mirror each row, flatten
            rows = [readings_fahrenheit[i:i+32] for i in range(0, len(readings_fahrenheit), 32)]
            mirrored = [x for row in rows for x in reversed(row)]

            return {
                "all_temperatures_celsius": readings_celsius,
                "all_temperatures_fahrenheit": readings_fahrenheit,
                "all_temperatures_fahrenheit_mirrored": mirrored,
                "min_temp_celsius": min(readings_celsius),
                "max_temp_celsius": max(readings_celsius),
                "min_temp_fahrenheit": min(readings_fahrenheit),
                "max_temp_fahrenheit": max(readings_fahrenheit),
            }

    async def close(self):
        """Stop the frame reading thread."""
        print("Closing MLX90640 sensor")
        if self._read_thread:
            self._stop_event.set()
            self._read_thread.join()
            self._read_thread = None

## Implementation of the Mlx90641 Camera
## this uses the sensor to create an resized image so you can see
## the thermal image it is producing
## The image is not appropriate for use in training models
class MlxCamera(Camera, EasyResource):
    """MLX90641 IR Camera Component."""
    MODEL: ClassVar[Model] = Model(
        ModelFamily("rand", "waveshare-thermal"), "mlx90641-ir-camera"
    )
    mlxsensor : Sensor
    heatmap_palette: List[int]
    _last_reading_time: float = 0
    _cached_image: Optional[ViamImage] = None
    _flipped: bool = False
    CACHE_DURATION = 0.001  # 10ms cache duration

    @classmethod
    def new(
      cls, config: ComponentConfig,
      dependencies: Mapping[ResourceName, ResourceBase]
      ) -> Self:
        mlxcamera = cls(config.name)
        mlxcamera.reconfigure(config, dependencies)
        return mlxcamera

    def reconfigure(
            self,
            config: ComponentConfig,
            dependencies: Mapping[ResourceName, ResourceBase]):
        """Reconfigure the MLX90640 sensor."""
        sensor_name = config.attributes.fields["sensor"].string_value
        if sensor_name == "":
            raise Exception(
                "An mlx90641-ir-sensor attribute is required for an mlx90641-ir-camera."
                )

        sensor = dependencies[Sensor.get_resource_name(sensor_name)]
        self.mlxsensor = cast(Sensor, sensor)
        self.heatmap_palette = utils.create_heatmap_palette()

        flipped = config.attributes.fields["flipped"].bool_value
        if flipped:
            self._flipped = True

    @classmethod
    def validate(cls, config: ComponentConfig):
        """Validate the MLX90641 IR Camera configuration."""
        sensor_name = config.attributes.fields["sensor"].string_value
        if sensor_name == "":
            raise Exception(
                "An mlx90641-ir-sensor attribute is required for an mlx90641-ir-camera."
                )
        return [sensor_name]

    async def get_image(
        self,
        mime_type: str = "",
        *,
        extra: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> ViamImage:
        current_time = time.time()

        # Return cached image if within cache duration
        if self._cached_image and (current_time - self._last_reading_time) < self.CACHE_DURATION:
            return self._cached_image

        readings = await self.mlxsensor.get_readings()
        if self._flipped:
            temperature = readings["all_temperatures_fahrenheit_mirrored"]
        else:
            temperature = readings["all_temperatures_celsius"]

        self._cached_image = utils.create_thermal_image(
            temperature,
            self.heatmap_palette,
            width=240,
            height=320
        )
        self._last_reading_time = current_time

        return self._cached_image

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
