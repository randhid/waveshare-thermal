import asyncio
import sys
from typing import (Any, ClassVar, Dict, Final, List, Mapping, Optional,
                    Sequence, Tuple)

from typing_extensions import Self
from viam.components.camera import Camera
from viam.media.video import NamedImage, ViamImage, CameraMimeType
from viam.module.module import Module
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import ResourceName, ResponseMetadata
from viam.proto.component.camera import GetPropertiesResponse
from viam.resource.base import ResourceBase
from viam.resource.easy_resource import EasyResource
from viam.resource.types import Model, ModelFamily
from PIL import Image
from io import BytesIO

import busio
import adafruit_mlx90640
import board
from viam.media.utils import pil
from viam.logging import getLogger
import numpy as np

LOGGER = getLogger(__name__)

class Mlx90641Ir(Camera, EasyResource):
    MODEL: ClassVar[Model] = Model(
        ModelFamily("rand", "waveshare-thermal"), "mlx90641-ir"
    )
    mlx = adafruit_mlx90640.MLX90640
    frame = []

    @classmethod
    def new(
        cls, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]
    ) -> Self:
        """This method creates a new instance of this vision service.
        The default implementation sets the name from the `config` 
        parameter and 
        then calls `reconfigure`.

        Args:
            config (ComponentConfig): The configuration for this resource
            dependencies (Mapping[ResourceName, ResourceBase]): The dependencies (both implicit and explicit)

        Returns:
            Self: The resource
        """

        i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)

        instance = cls(config.name)
        instance.mlx = adafruit_mlx90640.MLX90640(i2c)
        print("MLX addr detected on I2C", [hex(i) for i in instance.mlx.serial_number])
        instance.mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ
        instance.frame = [0] * 768

        return instance

    @classmethod
    def validate_config(cls, config: ComponentConfig) -> Sequence[str]:
        """This method allows you to validate the configuration object received from the machine,
        as well as to return any implicit dependencies based on that `config`.

        Args:
            config (ComponentConfig): The configuration for this resource

        Returns:
            Sequence[str]: A list of implicit dependencies
        """
        return

    def reconfigure(
        self, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]
    ):
        """This method allows you to dynamically update your service when it receives a new `config` object.

        Args:
            config (ComponentConfig): The new configuration
            dependencies (Mapping[ResourceName, ResourceBase]): Any dependencies (both implicit and explicit)
        """
        return

    async def get_image(
        self,
        mime_type: str = "",
        *,
        extra: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> ViamImage:
        try:
            # Capture the frame data from the MLX90640 sensor
            self.mlx.getFrame(self.frame)

            # Get min and max temperatures for normalization
            min_temp = min(self.frame)
            max_temp = max(self.frame)

            # Normalize the frame data to 0-255 grayscale
            normalized_frame = []
            for value in self.frame:
                normalized_value = int(255 * (value - min_temp) / (max_temp - min_temp))
                normalized_frame.append(normalized_value)

            # Convert the 1D normalized_frame into a 2D array (32x24)
            image_data = []
            for row in range(24):
                start_index = row * 32
                end_index = start_index + 32
                image_data.append(normalized_frame[start_index:end_index])
            np_array = np.array(image_data, dtype=np.uint8)  # dtype=np.uint8 for grayscale

            # 2. Convert the numpy array into a PIL image
            img = Image.fromarray(np_array)
            LOGGER.error(f"array shape is {np_array.shape}")

            viam_img = pil.pil_to_viam_image(img, mime_type=CameraMimeType.PNG)
            return viam_img
            # # Create a grayscale Pillow image from the 2D list
            # img = Image.new('L', (32, 24))  # 'L' mode for grayscale
            # pixels = img.load()
            # for row in range(24):
            #     for col in range(32):
            #         pixels[col, row] = image_data[row][col]

            # # Save the image as a JPEG to an in-memory buffer
            # img_buffer = BytesIO()
            # img.save(img_buffer, format="JPEG")
            # img_buffer.seek(0)  # Move the pointer to the start of the buffer

            # # Pass the JPEG byte data to ViamImage
            # return ViamImage(data=img_buffer.read(), mime_type=CameraMimeType.PNG)

        except Exception as e:
            print(f"Error capturing image: {e}")
            pass
        #     return ViamImage()
        
    
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
