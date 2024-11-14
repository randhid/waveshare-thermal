# [`rand:waveshare-thermal` module](<https://github.com/randhid/waveshare-thermal>)

This [module](https://docs.viam.com/registry/#modular-resources) implements the [`rdk:components:sensor` and the `rdk:components:camera` APIs] in <rand:waveshare-thermal:mlx90641-ir-sensor> and  <rand:waveshare-thermal:mlx90641-ir-camera> models.
With this module, you can use Waveshare's thermal cameras to detect temperatures and display an image of the associated heatmap that the IR lens senses from its environment.

*Note*: The associated heatmap from the camera has been resized from its 24x32 pixel array to make it easier to see. However, this resized image would be unsuitable for algorithms that require precise temperatures. Please configure a<rand:waveshare-thermal:mlx90641-ir-sensor> and use the sensor's [`GetReadings`](https://docs.viam.com/appendix/apis/components/sensor/#getreadings) method to extract accurate data from this device.

## Requirements

This module installs only on Raspberry Pi boards with Python >= 3.8, as RPi.GPIO is required for the current release.

The module should attempt to install `uv` to run, but if this Python package needs to be installed manually, you can install it with the following commands:
```bash
# On Linux.
$ curl -LsSf https://astral.sh/uv/install.sh | sh

```

```bash
# With pip.
$ pip install uv

```

## Configure your <rand:waveshare-thermal:mlx90641-ir-sensor> <rdk:component:sensor>

Navigate to the [**CONFIGURE** tab](https://docs.viam.com/configure/) of your [machine](https://docs.viam.com/fleet/machines/) in [the Viam app](https://app.viam.com/).
[Add `sensor`/ `waveshare-thermal:mlx90641-ir-sensor` to your machine](https://docs.viam.com/configure/#components).

No configuration attributes are required for the sensor.


## Configure your <rand:waveshare-thermal:mlx90641-ir-camera> <rdk:component:camera>

Navigate to the [**CONFIGURE** tab](https://docs.viam.com/configure/) of your [machine](https://docs.viam.com/fleet/machines/) in [the Viam app](https://app.viam.com/).
[Add `camera`/ `waveshare-thermal:mlx90641-ir-camera` to your machine](https://docs.viam.com/configure/#components).


On the new component panel, copy and paste the following attribute template into your camera's attributes field:

```json
{
  "sensor": "<sensor-name>",
},
"depends_on" : [ "<sensor-name>"]
```


### Attributes

The following attributes are available for `rand:waveshare-thermal:mlx90641-ir-camera` <rdk:component:camera>s:

| Name    | Type   | Required?    | Description |
| ------- | ------ | ------------ | ----------- |
| `sensor` | string | **Required** | Name of the configured  <rand:waveshare-thermal:mlx90641-ir-sensor> on your machine.|

### Example configuration

```json
{
  "components": [
    {
      "name": "sensor-1",
      "namespace": "rdk",
      "type": "sensor",
      "model": "rand:waveshare-thermal:mlx90641-ir-sensor",
      "attributes": {}
    },
    {
      "name": "camera-1",
      "namespace": "rdk",
      "type": "camera",
      "model": "rand:waveshare-thermal:mlx90641-ir-camera",
      "attributes": {
        "sensor": "sensor-1"
      },
      "depends_on": [
        "sensor-1"
      ]
    }
  ],
  "modules": [
    {
      "type": "registry",
      "name": "rand_waveshare-thermal",
      "module_id": "rand:waveshare-thermal",
      "version": "0.0.4"
    }
  ]
}
```

### Next steps
You can write code using this module using the [sensor](https://docs.viam.com/appendix/apis/components/sensor/) or [camera](https://www.google.com/search?q=viam+camera+api) Viam APIs. 

## Troubleshooting

Make sure that the I2C wires are connected to the [correct pins](https://pinout.xyz/ ): Connect the device's SDA to the SDA pin on the board and its SCL to the SCL pin on the Raspberry Pi.

When the device boots up, it follows a calibration sequence and will not show readings or an image immediately. Allow 5-10 seconds for the device to extract its calibration parameters and apply them, and then it will start measuring and reporting data. 
