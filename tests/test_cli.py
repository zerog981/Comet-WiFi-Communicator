from unittest.mock import patch

import pytest

from comet_wifi_communicator.cli import setup_thermostat


class TestCli:
    """Test suite for the setup_thermostat CLI command."""

    def test_with_all_arguments(self, mock_send_config_data):
        """Test setup_thermostat with all required and optional arguments."""
        test_args = [
            "setup_thermostat",
            "--wifi-ssid",
            "TestNetwork",
            "--wifi-password",
            "test_password_123",
            "--mqtt-server-ip",
            "192.168.1.100",
            "--mqtt-server-port",
            "8883",
        ]

        with patch("sys.argv", test_args):
            setup_thermostat()

        mock_send_config_data.assert_called_once_with(
            wifi_ssid="TestNetwork",
            wifi_password="test_password_123",
            mqtt_server_ip="192.168.1.100",
            mqtt_port=8883,
        )

    def test_with_default_mqtt_port(self, mock_send_config_data):
        """Test setup_thermostat uses default MQTT port when not specified."""
        test_args = [
            "setup_thermostat",
            "--wifi-ssid",
            "HomeNetwork",
            "--wifi-password",
            "secure_pass",
            "--mqtt-server-ip",
            "10.0.0.50",
        ]

        with patch("sys.argv", test_args):
            setup_thermostat()

        mock_send_config_data.assert_called_once_with(
            wifi_ssid="HomeNetwork",
            wifi_password="secure_pass",
            mqtt_server_ip="10.0.0.50",
            mqtt_port=1883,
        )

    def test_missing_required_argument(self, mock_send_config_data):
        """Test setup_thermostat exits with error when required arguments are missing."""
        test_args = [
            "setup_thermostat",
            "--wifi-ssid",
            "TestNetwork",
        ]

        with patch("sys.argv", test_args):
            with pytest.raises(SystemExit):
                setup_thermostat()

        mock_send_config_data.assert_not_called()
