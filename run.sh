#!/usr/bin/env sh

set -ex

# Ensure we're running on a Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
	echo "This script is intended to run on a Raspberry Pi."
	exit 1
fi

# Check if modprobe is installed
if ! command -v modprobe >/dev/null 2>&1; then
	echo "modprobe not found. Installing it..."
	
	# Install modprobe for Raspberry Pi (Debian-based system)
	sudo apt-get update && sudo apt-get install -y kmod
fi

# Ensure I2C is enabled
if ! lsmod | grep -q i2c_dev; then
	echo "I2C module not loaded. Loading i2c-dev..."
	sudo modprobe i2c-dev
fi


# Ensure I2C is enabled in the Raspberry Pi config
if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
	echo "Enabling I2C in /boot/config.txt..."
	echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt
	echo "Please Reboot your Raspberry Pi, we had to write to the device tree to enable I2C"
fi

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
