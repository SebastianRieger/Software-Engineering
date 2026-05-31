import logging
import re

from core.config import settings


_GESTURE_FRAME_SUCCESS_PATTERN = re.compile(r'"GET /api/v1/gestures/frame HTTP/[^"]+" 200\b')


def should_suppress_access_log(message: str) -> bool:
    if not settings.SUPPRESS_GESTURE_PREVIEW_ACCESS_LOGS:
        return False
    return _GESTURE_FRAME_SUCCESS_PATTERN.search(message) is not None


class SuppressNoisyAccessLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return not should_suppress_access_log(record.getMessage())


def _attach_uvicorn_access_filter() -> None:
    access_logger = logging.getLogger('uvicorn.access')

    for existing_filter in access_logger.filters:
        if isinstance(existing_filter, SuppressNoisyAccessLogFilter):
            break
    else:
        access_logger.addFilter(SuppressNoisyAccessLogFilter())

    for handler in access_logger.handlers:
        for existing_filter in handler.filters:
            if isinstance(existing_filter, SuppressNoisyAccessLogFilter):
                break
        else:
            handler.addFilter(SuppressNoisyAccessLogFilter())


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    _attach_uvicorn_access_filter()
