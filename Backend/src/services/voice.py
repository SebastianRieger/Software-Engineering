from datetime import datetime, timezone
import threading


class VoiceServiceError(Exception):
    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


class VoiceService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._running = False
        self._device_index: int | None = None
        self._last_command: str | None = None
        self._last_command_at: datetime | None = None
        self._last_error = "Mikrofonpfad ist noch nicht an eine echte Audioaufnahme angebunden."

    def startup(self) -> None:
        return None

    def get_status(self) -> dict[str, object]:
        with self._lock:
            return {
                "message": "Voice status",
                "available": False,
                "running": self._running,
                "mode": "skeleton",
                "provider": "vosk",
                "device_index": self._device_index,
                "last_command": self._last_command,
                "last_command_at": self._last_command_at,
                "last_error": self._last_error,
            }

    def start(self, device_index: int = 0) -> dict[str, object]:
        with self._lock:
            self._running = False
            self._device_index = device_index
            self._last_error = "Mikrofonpfad ist vorbereitet, aber noch nicht implementiert."

        raise VoiceServiceError(self._last_error, status_code=503)

    def stop(self) -> dict[str, object]:
        with self._lock:
            self._running = False
            self._device_index = None
            return {
                "message": "Voice stopped",
                "available": False,
                "running": False,
                "mode": "skeleton",
                "provider": "vosk",
                "device_index": None,
                "last_command": self._last_command,
                "last_command_at": self._last_command_at,
                "last_error": self._last_error,
            }

    def note_command(self, command: str) -> None:
        with self._lock:
            self._last_command = command
            self._last_command_at = datetime.now(timezone.utc)

    def shutdown(self) -> None:
        with self._lock:
            self._running = False
            self._device_index = None


voice_service = VoiceService()