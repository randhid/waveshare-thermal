#!/usr/bin/env python3
"""MLX90641 IR Thermal Sensor and Camera Components."""

import asyncio
import logging
import time
from typing import Any, ClassVar, Dict, List, Mapping, Optional, Tuple, Sequence, cast

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

import sensor
import utils

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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
        """Reconfigure the MLX90640 IR Camera."""
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
    def validate_config(cls, config: ComponentConfig) -> Sequence[str]:
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
        if self._cached_image and (current_time - self._last_reading_time) < sensor.CACHE_DURATION:
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
        return Camera.Properties(
            supports_pcd=False,
            distortion_parameters=[],
            intrinsic_parameters=[],
            width_px=240,
            height_px=320
        )
