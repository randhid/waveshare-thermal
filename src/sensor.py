#!/usr/bin/env python3
"""MLX90641 IR Thermal Sensor and Camera Components."""

import logging
import os
import time
from threading import Event, Lock, Thread
from typing import Any, ClassVar, List, Mapping, Optional

import adafruit_mlx90640
import board
import busio
from typing_extensions import Self
from viam.components.sensor import Sensor
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import ResourceName
from viam.resource.base import ResourceBase
from viam.resource.easy_resource import EasyResource
from viam.resource.types import Model, ModelFamily
from viam.utils import SensorReading

import utils

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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

CACHE_DURATION = 0.001  # 1ms cache duration
MAX_RETRIES = 3
BASE_DELAY = 0.05  # Base delay between retries in seconds

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
        """Continuously read frames from MLX sensor with retry logic"""
        retry_count = 0

        while not self._stop_event.is_set():
            try:
                current_time = time.time()
                # Check cache first
                if (current_time - self._last_reading_time) < CACHE_DURATION:
                    time.sleep(0.001)  # Small sleep to prevent tight loop
                    continue

                # Read frame from sensor
                start_time = time.time()
                self.mlx.getFrame(self._frame_buffer)

                # Log success and reset retry count
                read_time = (time.time() - start_time) * 1000
                logger.debug(f"Frame read successful in {read_time:.1f}ms")
                retry_count = 0

                # Update frame buffer with lock
                with self._frame_lock:
                    self._last_frame = self._frame_buffer.copy()
                    self._last_reading_time = time.time()

            except (OSError, Exception) as e:
                retry_count += 1
                logger.error(f"Frame read failed: {e} (retry {retry_count})")

                if retry_count >= MAX_RETRIES:
                    logger.error("Max retries exceeded, waiting longer...")
                    time.sleep(BASE_DELAY * 2)
                    retry_count = 0
                else:
                    time.sleep(BASE_DELAY)

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

        # Set the refresh rate with fallback
        refresh_rate = config.attributes.fields["refresh_rate_hz"].number_value
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
            "min_temp_celsius": min(readings_celsius),
            "max_temp_celsius": max(readings_celsius),
            "min_temp_fahrenheit": min(readings_fahrenheit),
            "max_temp_fahrenheit": max(readings_fahrenheit),
            "all_temperatures_celsius": readings_celsius,
            "all_temperatures_fahrenheit": readings_fahrenheit,
            "all_temperatures_fahrenheit_mirrored": mirrored,
            }

    async def close(self):
        """Stop the frame reading thread."""
        print("Closing MLX90640 sensor")
        if self._read_thread:
            self._stop_event.set()
            self._read_thread.join()
            self._read_thread = None
