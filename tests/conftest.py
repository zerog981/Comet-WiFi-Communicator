"""Shared pytest configuration and fixtures."""

from unittest.mock import patch, MagicMock

import pytest

from comet_wifi_communicator.thermostat import Thermostat, ThermostatConfig


@pytest.fixture
def mock_mqtt_client():
    """Mock MQTT client to avoid real connections."""
    with patch("comet_wifi_communicator.thermostat.Client") as mock:
        yield mock.return_value

@pytest.fixture
def thermostat(mock_mqtt_client):
    """Create a Thermostat instance with mocked MQTT client."""
    return Thermostat(
        mqtt_host="192.168.1.100",
        mqtt_port=1883,
        mac="AA:BB:CC:DD:EE:FF",
    )

@pytest.fixture
def config():
    """Create a ThermostatConfig instance."""
    return ThermostatConfig()

@pytest.fixture
def mock_socket():
    """Patch socket.socket and return the mock instance."""
    mock_socket = MagicMock()
    with patch("comet_wifi_communicator.setup_thermostat.socket.socket", return_value=mock_socket):
        yield mock_socket


@pytest.fixture
def mock_sleep():
    """Patch time.sleep to speed up tests."""
    with patch("comet_wifi_communicator.setup_thermostat.time.sleep"):
        yield