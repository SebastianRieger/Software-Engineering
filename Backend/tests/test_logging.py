from core.logging import should_suppress_access_log


def test_should_suppress_access_log_for_successful_gesture_frame_requests():
    message = '127.0.0.1:12345 - "GET /api/v1/gestures/frame HTTP/1.1" 200'
    assert should_suppress_access_log(message) is True


def test_should_not_suppress_access_log_for_non_frame_requests():
    message = '127.0.0.1:12345 - "GET /api/v1/gestures/status HTTP/1.1" 200'
    assert should_suppress_access_log(message) is False


def test_should_not_suppress_access_log_for_frame_errors():
    message = '127.0.0.1:12345 - "GET /api/v1/gestures/frame HTTP/1.1" 404'
    assert should_suppress_access_log(message) is False