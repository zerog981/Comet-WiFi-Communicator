import pytest
import socket
from unittest.mock import Mock, patch, MagicMock, call

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
    #
    # @patch("comet_wifi_communicator.communicator.socket.socket")
    # @patch("comet_wifi_communicator.communicator.time.sleep")

    #
    # @patch("comet_wifi_communicator.communicator.socket.socket")
    # @patch("comet_wifi_communicator.communicator.time.sleep")
    # def test_custom_endpoint(self, mock_sleep, mock_socket_class, mock_socket):
    #     """Test connection to custom Comet WiFi endpoint."""
    #     mock_socket_class.return_value = mock_socket
    #
    #     send_config_data(
    #         wifi_ssid="TestNetwork",
    #         wifi_password="TestPass123",
    #         comet_wifi_ip="192.168.1.50",
    #         comet_wifi_port=5000,
    #     )
    #
    #     mock_socket.connect.assert_called_once_with(("192.168.1.50", 5000))
    #
    # @patch("comet_wifi_communicator.communicator.socket.socket")
    # @patch("comet_wifi_communicator.communicator.time.sleep")
    # def test_mqtt_port_hex_padding(
    #     self, mock_sleep, mock_socket_class, mock_socket
    # ):
    #     """Test that MQTT port is zero-padded to 4 hex digits."""
    #     mock_socket_class.return_value = mock_socket
    #
    #     send_config_data(
    #         wifi_ssid="Test",
    #         wifi_password="Pass",
    #         mqtt_port=11,
    #     )
    #
    #     # Capture the data sent
    #     call_args = mock_socket.sendall.call_args[0][0]
    #
    #     # Verify port is padded correctly
    #     expected_port = int_to_hex_str(11, uppercase=True).zfill(4)
    #     assert expected_port in call_args
    #     # Verify sendall was called (data formatting happened)
    #     mock_socket.sendall.assert_called_once()
