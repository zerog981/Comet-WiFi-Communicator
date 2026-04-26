"""Test MQTT connection handling."""

import pytest
from unittest.mock import Mock
from paho.mqtt.client import CONNACK_ACCEPTED
from comet_wifi_communicator.thermostat import MQTTConnectError


class TestMqttConnection:
    """Test MQTT connection handling."""

    def test_on_mqtt_connect_success(self, thermostat):
        """Successful connection subscribes to all reply topics."""
        mock_client = Mock()
        reason_code = CONNACK_ACCEPTED

        thermostat._on_mqtt_connect(mock_client, None, None, reason_code.value)

        assert (
            mock_client.subscribe.call_count == len(thermostat._topics.reply_topics) + 1
        )

    def test_on_mqtt_connect_failure_raises_error(self, thermostat):
        """Connection failure (reason_code != 0) raises MQTTConnectError."""
        mock_client = Mock()
        with pytest.raises(MQTTConnectError):
            thermostat._on_mqtt_connect(mock_client, None, None, reason_code=1)

    @pytest.mark.asyncio
    async def test_connect_starts_loop(self, thermostat, mock_mqtt_client):
        """Make sure thermostat.connect() calls connect() and loop_start()."""
        await thermostat.connect()
        mock_mqtt_client.connect.assert_called_once_with("192.168.1.100", 1883)
        mock_mqtt_client.loop_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_stops_loop(self, thermostat, mock_mqtt_client):
        """Make sure thermostat.disconnect() calls disconnect() and loop_stop()."""
        await thermostat.disconnect()

        mock_mqtt_client.disconnect.assert_called_once()
        mock_mqtt_client.loop_stop.assert_called_once()
        assert thermostat.connected is False
