import logging
import threading
from collections.abc import Mapping
from typing import Protocol

from core.realtime import realtime_hub


logger = logging.getLogger(__name__)


try:
    from gpiozero import PWMLED
except ImportError:
    PWMLED = None


class LEDAdapterError(Exception):
    pass


class LEDAdapter(Protocol):
    def is_available(self) -> bool:
        ...

    def open(self) -> None:
        ...

    def apply(self, red: float, green: float, blue: float, brightness: float) -> None:
        ...

    def close(self) -> None:
        ...


class GpiozeroLEDAdapter:
    def __init__(self, red_pin: int = 17, green_pin: int = 27, blue_pin: int = 22) -> None:
        self.red_pin = red_pin
        self.green_pin = green_pin
        self.blue_pin = blue_pin
        self.red = None
        self.green = None
        self.blue = None

    def is_available(self) -> bool:
        return PWMLED is not None

    def open(self) -> None:
        if not self.is_available():
            raise LEDAdapterError("gpiozero PWMLED ist in dieser Umgebung nicht verfuegbar.")

        try:
            self.red = PWMLED(self.red_pin)
            self.green = PWMLED(self.green_pin)
            self.blue = PWMLED(self.blue_pin)
        except Exception as exc:
            raise LEDAdapterError(f"GPIO-LED konnte nicht initialisiert werden: {exc}") from exc

    def apply(self, red: float, green: float, blue: float, brightness: float) -> None:
        if self.red is None or self.green is None or self.blue is None:
            raise LEDAdapterError("GPIO-LED ist nicht initialisiert.")

        try:
            self.red.value = red * brightness
            self.green.value = green * brightness
            self.blue.value = blue * brightness
        except Exception as exc:
            raise LEDAdapterError(f"GPIO-LED Zustand konnte nicht gesetzt werden: {exc}") from exc

    def close(self) -> None:
        for channel in (self.red, self.green, self.blue):
            if channel is not None:
                try:
                    channel.close()
                except RuntimeError:
                    logger.debug("LED channel close failed", exc_info=True)
        self.red = None
        self.green = None
        self.blue = None


class LEDService:
    def __init__(self, adapter_factory=None):
        self.adapter_factory = adapter_factory or GpiozeroLEDAdapter
        self._adapter: LEDAdapter | None = None
        self._lock = threading.Lock()
        self._started = False
        self._state = {
            "red": 0.0,
            "green": 0.0,
            "blue": 0.0,
            "brightness": 1.0,
            "available": False,
            "mode": "mock",
            "last_error": None,
        }

    def startup(self) -> None:
        with self._lock:
            if self._started:
                return

            self._started = True
            self._initialize_adapter_locked()

    def ensure_started(self) -> None:
        if not self._started:
            self.startup()

    def get_status(self) -> dict[str, object]:
        self.ensure_started()
        with self._lock:
            return self._snapshot_locked(message="LED status")

    def set_color(self, rgb: tuple[float, float, float]) -> dict[str, object]:
        self.ensure_started()
        with self._lock:
            red, green, blue = rgb
            self._state["red"] = float(red)
            self._state["green"] = float(green)
            self._state["blue"] = float(blue)
            self._apply_state_locked()
            snapshot = self._snapshot_locked(message="LED color set")

        self._publish_state_changed(snapshot)
        return snapshot

    def set_brightness(self, brightness: float) -> dict[str, object]:
        self.ensure_started()
        with self._lock:
            self._state["brightness"] = float(brightness)
            self._apply_state_locked()
            snapshot = self._snapshot_locked(message="LED brightness set")

        self._publish_state_changed(snapshot)
        return snapshot

    def shutdown(self) -> None:
        with self._lock:
            if self._adapter is not None:
                self._adapter.close()
                self._adapter = None
            self._started = False

    def _initialize_adapter_locked(self) -> None:
        try:
            adapter = self.adapter_factory()
            if not adapter.is_available():
                self._adapter = None
                self._state["available"] = False
                self._state["mode"] = "mock"
                self._state["last_error"] = "GPIO-LED-Hardware ist in dieser Umgebung nicht verfuegbar."
                return

            adapter.open()
            self._adapter = adapter
            self._state["available"] = True
            self._state["mode"] = "hardware"
            self._state["last_error"] = None
            self._apply_state_locked()
        except LEDAdapterError as exc:
            logger.warning("LED hardware initialization failed: %s", exc)
            self._adapter = None
            self._state["available"] = False
            self._state["mode"] = "mock"
            self._state["last_error"] = str(exc)

    def _apply_state_locked(self) -> None:
        if self._adapter is None:
            return

        try:
            self._adapter.apply(
                red=float(self._state["red"]),
                green=float(self._state["green"]),
                blue=float(self._state["blue"]),
                brightness=float(self._state["brightness"]),
            )
            self._state["available"] = True
            self._state["mode"] = "hardware"
            self._state["last_error"] = None
        except LEDAdapterError as exc:
            logger.warning("LED hardware apply failed: %s", exc)
            self._adapter.close()
            self._adapter = None
            self._state["available"] = False
            self._state["mode"] = "mock"
            self._state["last_error"] = str(exc)

    def _snapshot_locked(self, message: str) -> dict[str, object]:
        return {
            "message": message,
            **self._state,
        }

    @staticmethod
    def _publish_state_changed(snapshot: Mapping[str, object]) -> None:
        realtime_hub.publish_from_thread(
            {
                "eventType": "LEDStateChanged",
                "payload": dict(snapshot),
            }
        )


led_service = LEDService()