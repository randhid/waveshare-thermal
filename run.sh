#!/usr/bin/env sh

set -ex

# Ensure we're running on a Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
	echo "This script is intended to run on a Raspberry Pi."
	exit 1
fi

# Check the current I2C setting
i2c_status=$(sudo raspi-config nonint get_i2c)
if [ $i2c_status -eq 1 ]; then
    echo "I2C is disabled. Enabling it now..."
    sudo raspi-config nonint do_i2c 0
    if [ $? -eq 0 ]; then
        echo "I2C has been successfully enabled. Please reboot the system."
    else
        echo "Failed to enable I2C. Please check your configuration."
        exit 1
    fi
else
    echo "I2C is already enabled in configuration, but the device file is missing."
    echo "Try rebooting the system or check for hardware issues."
fi

# Check if the I2C device file exists
if [ -e /dev/i2c-1 || -e /dev/i2c/1 ]; then
    echo "I2C device is already enabled."
    exit 0
fi

echo "I2C device not found. Checking I2C configuration..."

#  ~~~~~~~
# Keeping this here for potential future boards that do not use raspi-config - this 
# in't currently possible because of the RPi.GPIO dependency wihin the adafruit library we're using
# and converting the code to do everythign that the library does in terms of calibration 
# and offsetting of pixels is a lot of time that we should only do if we know we're going to need to run this 
# particular hardware on another board. 
# Would have to happen when i2c fails.
#  ~~~~~~~

# # Check if modprobe is installed
# if ! command -v modprobe >/dev/null 2>&1; then
# 	echo "modprobe not found. Installing it..."
	
# 	# Install modprobe for Raspberry Pi (Debian-based system)
# 	sudo apt-get update && sudo apt-get install -y kmod
# fi

# # Ensure I2C is enabled
# if ! lsmod | grep -q i2c_dev; then
# 	echo "I2C module not loaded. Loading i2c-dev..."
# 	sudo modprobe i2c-dev
# fi

#  ~~~~~~
#  Keeping the nuclear option here because that's what definitley worked in release 0.0.5
# This is disruptive and reboots the pi as modules are loading
#  ~~~~~~~
# # Ensure I2C is enabled in the Raspberry Pi config
# if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
# 	echo "Enabling I2C in /boot/config.txt..."
# 	echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt
# 	echo "Please Reboot your Raspberry Pi, we had to write to the device tree to enable I2C"
# fi

# uv gets installed in this folder
export PATH=$PATH:$HOME/.local/bin

if [ ! $(command -v uv) ]; then
	if [ ! $(command -v curl) ]; then
		echo need curl to install UV. please install curl on this system.
		exit 1
	fi
	curl -LsSf https://astral.sh/uv/install.sh | sh
fi

if [ ! -d .venv ]; then
	uv venv --python=3.12
fi
uv pip sync requirements.txt
exec .venv/bin/python src/main.py $@
