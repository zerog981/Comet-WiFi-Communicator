"""Shared pytest configuration and fixtures."""

from unittest.mock import patch, MagicMock

import pytest


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

@pytest.fixture
def mock_send_config_data():
    """Fixture that mocks send_config_data function."""
    with patch("comet_wifi_communicator.cli.send_config_data") as mock:
        yield mock