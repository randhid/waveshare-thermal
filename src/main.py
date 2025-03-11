#!/usr/bin/env python3
"""MLX90641 IR Thermal Sensor and Camera Components."""

import asyncio
import logging
from threading import Event, Lock, Thread

from viam.module.module import Module

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if __name__ == "__main__":
    asyncio.run(Module.run_from_registry())
