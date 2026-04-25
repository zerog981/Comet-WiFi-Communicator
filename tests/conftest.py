"""Shared pytest configuration and fixtures."""

import pytest
from unittest.mock import patch

from comet_wifi_communicator.thermostat import ThermostatConfig


@pytest.fixture
def mock_mqtt_client():
    """Mock MQTT client to avoid real connections."""
    with patch("src.comet_wifi_communicator.thermostat.Client") as mock:
        yield mock.return_value

@pytest.fixture
def thermostat(mock_mqtt_client):
    """Create a Thermostat instance with mocked MQTT client."""
    from src.comet_wifi_communicator.thermostat import Thermostat

    return Thermostat(
        mqtt_host="192.168.1.100",
        mqtt_port=1883,
        mac="AA:BB:CC:DD:EE:FF",
    )

@pytest.fixture
def config():
    """Create a ThermostatConfig instance."""
    return ThermostatConfig()