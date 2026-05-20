import pytest
import socket
from unittest.mock import Mock, patch, MagicMock, call, ANY

from comet_wifi_communicator.setup_thermostat import send_config_data
from comet_wifi_communicator.helper import (
    ip_to_hex_str,
    string_to_unicode,
    int_to_hex_str,
)


class TestSendConfigData:
    """Test suite for send_config_data."""

    def test_happy_path(self, mock_sleep, mock_socket):
        """Test successful configuration data transmission."""
        result = send_config_data(
            wifi_ssid="TestNetwork",
            wifi_password="TestPass123",
            mqtt_server_ip="192.168.0.1",
            mqtt_port=1883,
        )

        assert result is True
        mock_socket.connect.assert_called_once_with(("10.0.0.1", 1233))
        mock_socket.sendall.assert_called_once()
        mock_socket.close.assert_called_once()

    def test_connection_timeout(self, mock_socket):
        """Test handling of connection timeout."""
        mock_socket.connect.side_effect = socket.timeout("Connection timed out")

        result = send_config_data(
            wifi_ssid="TestNetwork",
            wifi_password="TestPass123",
        )

        assert result is False
        mock_socket.close.assert_called_once()

    def test_send_timeout(self, mock_sleep, mock_socket):
         """Test handling of send timeout."""
         mock_socket.connect = Mock()
         mock_socket.sendall.side_effect = socket.timeout("Send timed out")

         result = send_config_data(
             wifi_ssid="TestNetwork",
             wifi_password="TestPass123",
         )

         assert result is False
         mock_socket.close.assert_called_once()

    def test_socket_close_on_exception(self, mock_sleep, mock_socket):
        """Test that socket is closed even if sendall raises an exception."""
        mock_socket.sendall.side_effect = Exception("Unexpected error")

        with pytest.raises(Exception):
            send_config_data(
                wifi_ssid="TestNetwork",
                wifi_password="TestPass123",
            )

        mock_socket.close.assert_called_once()

    def test_data_formatting(self, mock_sleep, mock_socket):
        """Test that data is formatted correctly before sending."""

        send_config_data(
            wifi_ssid="MySSID",
            wifi_password="MyPass",
            mqtt_server_ip="10.0.0.1",
            mqtt_user="A0B1C2",
            mqtt_password="ABCDEF",
            mqtt_port=1883,
        )

        call_args = mock_socket.sendall.call_args[0][0]

        expected_ssid = string_to_unicode("MySSID", uppercase=True).encode()
        expected_pass = string_to_unicode("MyPass", uppercase=True).encode()
        expected_ip = ip_to_hex_str("10.0.0.1", uppercase=True).encode()
        expected_port = int_to_hex_str(1883, uppercase=True).encode()

        assert expected_ssid in call_args
        assert expected_pass in call_args
        assert expected_ip in call_args
        assert expected_port in call_args

    def test_custom_thermostat_ip(self, mock_sleep, mock_socket):
        """Test connection to custom Comet WiFi address."""
        send_config_data(
            wifi_ssid="TestNetwork",
            wifi_password="TestPass123",
            comet_wifi_ip="192.168.1.50",
            comet_wifi_port=5000,
        )
        mock_socket.connect.assert_called_once_with(("192.168.1.50", 5000))

    def test_logger_none_does_not_raise(self, mock_sleep, mock_socket):
        """Test function executes without error when logger=None."""
        result = send_config_data(
            wifi_ssid="TestNetwork", wifi_password="TestPass123", logger=None
        )

        assert result is True
        mock_socket.close.assert_called_once()

    def test_logger_calls_on_success(self, mock_sleep, mock_socket):
        """Test logger calls occur in correct sequence on success."""
        mock_logger = Mock()

        send_config_data(
            wifi_ssid="TestNetwork", wifi_password="TestPass123", logger=mock_logger
        )

        expected_calls = [
            call(ANY),  # Initial SSID/MQTT/Comet info
            call("Configuring connection."),
            call("Successfully connected to thermostat."),
            call("Sending data."),
            call("Data successfully transmitted."),
        ]
        mock_logger.info.assert_has_calls(expected_calls, any_order=False)

    def test_logger_error_on_connection_timeout(self, mock_socket):
        """Test logger.error() on connection timeout."""
        mock_socket.connect.side_effect = socket.timeout()
        mock_logger = Mock()

        result = send_config_data(
            wifi_ssid="TestNetwork", wifi_password="TestPass123", logger=mock_logger
        )

        assert result is False
        mock_logger.error.assert_called_once_with("Unable to connect to thermostat")

    def test_logger_error_on_send_timeout(self, mock_sleep, mock_socket):
        """Test logger.error() on send timeout."""
        mock_socket.sendall.side_effect = socket.timeout()
        mock_logger = Mock()

        result = send_config_data(
            wifi_ssid="TestNetwork", wifi_password="TestPass123", logger=mock_logger
        )

        assert result is False
        mock_logger.error.assert_called_once_with("Error sending data.")

    def test_logger_mqtt_broker_info_logged(self, mock_sleep, mock_socket):
        """Test MQTT broker details are logged correctly."""
        mock_logger = Mock()

        send_config_data(
            wifi_ssid="MySSID",
            wifi_password="MyPass",
            mqtt_server_ip="192.168.1.100",
            mqtt_port=8883,
            logger=mock_logger,
        )
        first_info_call = mock_logger.info.call_args_list[0][0][0]
        assert "192.168.1.100:8883" in first_info_call
        assert "MySSID" in first_info_call

    def test_logger_comet_endpoint_info_logged(self, mock_sleep, mock_socket):
        """Test Comet thermostat address details are logged."""
        mock_logger = Mock()

        send_config_data(
            wifi_ssid="TestNetwork",
            wifi_password="TestPass123",
            comet_wifi_ip="192.168.1.50",
            comet_wifi_port=5000,
            logger=mock_logger,
        )

        first_info_call = mock_logger.info.call_args_list[0][0][0]
        assert "192.168.1.50:5000" in first_info_call