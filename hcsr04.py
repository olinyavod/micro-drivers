from machine import Pin
from pyb import micros
from utime import sleep_us
import uasyncio as asyncio
import micropython

__version__ = '0.0.1'
__author__ = 'Kirill Zhuravlev'
__license__ = "Apache License 2.0. https://www.apache.org/licenses/LICENSE-2.0"


class HCSR04:

    def __init__(self, trigger_pin, echo_pin, echo_timeout_us=500 * 2 * 30):
        self.echo_timeout_us = echo_timeout_us
        # Init trigger pin (out)
        self.trigger = Pin(trigger_pin, mode=Pin.OUT)
        self.trigger.value(0)

        # Init echo pin (in)
        self.echo = Pin(echo_pin, mode=Pin.IN)
        self.echo.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self.echo_on_changed)
        self.pulse_start = 0
        self.pulse_end = 0
        self.dist_filter = 0
        self.event = asyncio.ThreadSafeFlag()

    async def _send_pulse_and_wait(self) -> (bool, int):
        self.pulse_start = micros()
        self.pulse_end = 0
        self.trigger.value(0)  # Stabilize the sensor
        sleep_us(10)
        self.trigger.value(1)
        # Send a 10us pulse.
        sleep_us(10)
        self.trigger.value(0)

        try:
            await asyncio.wait_for_ms(self.event.wait(), int(self.echo_timeout_us / 1000))

            delta = self.pulse_end - self.pulse_start

            if delta < 0:
                return  True, self.echo_timeout_us

            self.dist_filter += (delta - self.dist_filter)
            return False, delta
        except asyncio.TimeoutError:
            return True, self.echo_timeout_us
        except OSError as ex:
            if ex.args[0] == 110:  # 110 = ETIMEDOUT
                raise OSError('Out of range')
            raise ex

    async def distance_mm(self) -> (bool, int):
        has_error, pulse_time = await self._send_pulse_and_wait()

        mm = pulse_time * 100.0 // 582.0
        return has_error, mm

    async def distance_cm(self) -> (bool, float):
        has_error, pulse_time = await self._send_pulse_and_wait()
        cms = (pulse_time / 2.0) / 29.1
        return has_error, cms

    @micropython.native
    def echo_on_changed(self, pin: Pin) -> None:
        if pin.value() == 1:
            self.pulse_start = micros()
        else:
            self.pulse_end = micros()
            self.event.set()
