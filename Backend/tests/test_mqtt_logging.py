import logging
from unittest.mock import Mock

import pytest

from services.mqtt import MQTTService


def test_on_connect_logs_success_and_subscribes(caplog):
    service = MQTTService()
    service.client.subscribe = Mock()

    with caplog.at_level(logging.INFO):
        service._on_connect(None, None, None, 0)

    assert 'Connected to MQTT broker' in caplog.text
    service.client.subscribe.assert_called_once_with('nimrag/#')


def test_on_connect_logs_warning_for_failed_result_code(caplog):
    service = MQTTService()
    service.client.subscribe = Mock()

    with caplog.at_level(logging.WARNING):
        service._on_connect(None, None, None, 5)

    assert 'Failed to connect to MQTT broker with code 5' in caplog.text
    service.client.subscribe.assert_not_called()


@pytest.mark.asyncio
async def test_connect_logs_warning_when_client_connect_raises(caplog):
    service = MQTTService()
    service.client.connect = Mock(side_effect=RuntimeError('boom'))
    service.client.loop_start = Mock()

    with caplog.at_level(logging.WARNING):
        await service.connect()

    assert 'Failed to connect to MQTT broker: boom' in caplog.text
    service.client.loop_start.assert_not_called()