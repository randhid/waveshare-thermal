# [`rand:waveshare-thermal` module](<https://github.com/randhid/waveshare-thermal>)

This [module](https://docs.viam.com/registry/#modular-resources) implements the [`rdk:components:sensor` and the `rdk:components:camera` API] in <rand:waveshare-thermal:mlx90461-ir-sensor> and  <rand:waveshare-thermal:mlx90461-ir-camera> models.
With this model, you can use waveshar'es thermal cameras to sensor temperatures and show an image of the associated heatmap that the IR lens is sensing from its environment. 

Note: the associated heatmap from the camera has been resized from it's 24x32 pixel array so that is is easier to see, and would be unsuitable for use in algorirthms that need accurate temperatures from the sensor. Please configure a  <rand:waveshare-thermal:mlx90461-ir-sensor> and use the sensor's [`GetReadings`](https://docs.viam.com/appendix/apis/components/sensor/#getreadings) method to extract accurate data from this device.

## Requirements

The module only installs on a Rapsberry Pi boards with Python >= 3.8 as RPi.GPIO is required for the current release.

The module should try to install uv to run, but should that python package need to be insatlled, you can install it with:

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

No configuration attirbutes are required for the sensor.


## Configure your <rand:waveshare-thermal:mlx90641-ir-camera> <rdk:component:camera>

Navigate to the [**CONFIGURE** tab](https://docs.viam.com/configure/) of your [machine](https://docs.viam.com/fleet/machines/) in [the Viam app](https://app.viam.com/).
[Add `camera`/ `waveshare-thermal:mlx90641-ir-camera` to your machine](https://docs.viam.com/configure/#components).


On the new component panel, copy and paste the following attribute template into your base’s attributes field:

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
You can wirte code using this module using the [sensor](https://docs.viam.com/appendix/apis/components/sensor/) or [camera](https://www.google.com/search?q=viam+camera+api) viam APIs. 

## Troubleshooting

Make sure that the i2c wires are connected to the [correct pins](https://pinout.xyz/) - SDA of the device to the SDA pin on the baord, and SCL pin from the device to the SCL pin on the Raspberry Pi board.

When the device boots up, it follows a calibration sequence and will not show readings or an aimage immediately, allows 5-10 seconds for the device to extract it's calirbation parameters and apply them, then it will starts measuring and reporting data. 