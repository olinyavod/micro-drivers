import time

from machine import Pin
from micropython import schedule, const

_RELEASE_STATE_ = const(0)
_PRESSED_STATE_ = const(1)


class Button:
    def __init__(self, pin, min_press_ms=100):
        self._on_changed_ref = self._on_changed
        self._pressed_us = 0
        self._pin = Pin(pin, Pin.IN, Pin.PULL_UP)
        self._pin.irq(self._button_irq, Pin.IRQ_RISING | Pin.IRQ_FALLING)
        self._state = _RELEASE_STATE_
        self._on_pressed = None
        self._min_press_ms = min_press_ms

    def on_pressed(self, handler):
        self._on_pressed = handler

    def _on_changed(self, value: int) -> None:
        print("Button on changed with state: ", self._state)
        if self._state == _RELEASE_STATE_ and value == 0:
            self._pressed_us = time.ticks_ms()
            self._state = _PRESSED_STATE_
        elif self._state == _PRESSED_STATE_ and value == 1:
            self._state = _RELEASE_STATE_
            delta = time.ticks_diff(time.ticks_ms(),self._pressed_us)

            print(f"Button release with delta: {delta} us")

            if delta < self._min_press_ms or self._on_pressed is None:
                return

            self._on_pressed(delta)

    def _button_irq(self, pin: Pin) -> None:
        value = pin.value()
        schedule(self._on_changed_ref, value)
