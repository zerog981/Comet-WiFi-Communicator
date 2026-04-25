"""Test temperature control functionality."""

import pytest

from comet_wifi_communicator.lib.const import (
    TEMPERATURE_HEX_OFF,
    TEMPERATURE_HEX_ON,
    HEX_PREFIX,
    TEMPERATURE_SETPOINT_MAX,
    TEMPERATURE_SETPOINT_MIN,
)


class TestTemperatureControl:
    """Test setting temperature and heating control."""

    @pytest.mark.asyncio
    async def test_set_temperature_within_bounds(self, thermostat, mock_mqtt_client):
        """Test if set_temperature publishes valid temperature."""
        thermostat._connected = True
        await thermostat.set_temperature(21.5)

        assert mock_mqtt_client.publish.called
        call_args = mock_mqtt_client.publish.call_args_list[0]
        topic = call_args[0][0]
        payload = call_args[0][1]
        assert "A0" in topic
        assert payload == "#2B"

    @pytest.mark.asyncio
    async def test_set_temperature_clamps_max(self, thermostat, mock_mqtt_client):
        """Test if set_temperature clamps to maximum."""
        thermostat._connected = True
        await thermostat.set_temperature(35.0)

        call_args = mock_mqtt_client.publish.call_args_list[0]
        payload = call_args[0][1]
        assert payload == f"{HEX_PREFIX}{hex(int(TEMPERATURE_SETPOINT_MAX * 2))[2:].upper()}" # "#38"

    @pytest.mark.asyncio
    async def test_set_temperature_clamps_min(self, thermostat, mock_mqtt_client):
        """Test if set_temperature clamps to minimum."""
        thermostat._connected = True
        await thermostat.set_temperature(5.0)

        call_args = mock_mqtt_client.publish.call_args_list[0]
        payload = call_args[0][1]
        assert payload == f"{HEX_PREFIX}{hex(int(TEMPERATURE_SETPOINT_MIN * 2))[2:].upper()}" # "#10"

    @pytest.mark.asyncio
    async def test_set_temperature_not_connected(self, thermostat):
        """Test if set_temperature raises when not connected."""
        thermostat._connected = False
        with pytest.raises(ConnectionError):
            await thermostat.set_temperature(20.0)

    @pytest.mark.asyncio
    async def test_turn_off(self, thermostat, mock_mqtt_client):
        """Test if turn_off publishes OFF command."""
        thermostat._connected = True
        await thermostat.turn_off()

        call_args = mock_mqtt_client.publish.call_args_list[0]
        payload = call_args[0][1]
        assert payload == f"{HEX_PREFIX}{TEMPERATURE_HEX_OFF:02X}"

    @pytest.mark.asyncio
    async def test_turn_off_not_connected(self, thermostat):
        """Test if turn_off raises when not connected."""
        thermostat._connected = False
        with pytest.raises(ConnectionError):
            await thermostat.turn_off()

    @pytest.mark.asyncio
    async def test_turn_fully_on(self, thermostat, mock_mqtt_client):
        """Test if turn_fully_on publishes ON command."""
        thermostat._connected = True
        await thermostat.turn_fully_on()

        call_args = mock_mqtt_client.publish.call_args_list[0]
        payload = call_args[0][1]
        assert payload == f"{HEX_PREFIX}{TEMPERATURE_HEX_ON:02X}"

    @pytest.mark.asyncio
    async def test_turn_fully_on_not_connected(self, thermostat):
        """Test if turn_fully_on raises when not connected."""
        thermostat._connected = False
        with pytest.raises(ConnectionError):
            await thermostat.turn_fully_on()

