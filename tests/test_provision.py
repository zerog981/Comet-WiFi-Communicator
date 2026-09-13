"""Tests for the provisioning module."""

import socket
from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest

from comet_wifi_communicator.provision import (
    THERMOSTAT_ADDRESS,
    InvalidSettingsError,
    ThermostatUnreachableError,
    build_payload,
    provision,
    send_payload,
)

PAYLOAD = (
    b"4D79576946692C7333637265742D7061737321,00000000,0000000000000000,C0A8B202,075B"
)


@pytest.fixture
def fake_socket() -> Iterator[MagicMock]:
    """Replace the TCP connection with a mock and skip the send grace period."""
    sock = MagicMock()
    with (
        patch(
            "comet_wifi_communicator.provision.socket.create_connection",
            return_value=sock,
        ) as create_connection,
        patch("comet_wifi_communicator.provision.time.sleep"),
    ):
        sock.__enter__.return_value = sock
        sock.create_connection = create_connection
        yield sock


class TestBuildPayload:
    """Tests for encoding the configuration message."""

    def test_golden(self) -> None:
        """Payload is matched."""
        payload = build_payload("MyWiFi", "s3cret-pass!", "192.168.178.2", 1883)
        assert payload == PAYLOAD

    @pytest.mark.parametrize(
        ("ssid", "password", "ip", "port", "expected"),
        [
            (
                "Home Net",
                "p@ss word",
                "10.0.0.5",
                8883,
                b"486F6D65204E65742C7040737320776F7264,00000000,0000000000000000,0A000005,22B3",
            ),
            ("A", "", "172.16.0.1", 1, b"412C,00000000,0000000000000000,AC100001,0001"),
        ],
    )
    def test_encoding(
        self, ssid: str, password: str, ip: str, port: int, expected: bytes
    ) -> None:
        """Spaces, an empty password, and short values are correctly encoded."""
        assert build_payload(ssid, password, ip, port) == expected

    def test_default_port(self) -> None:
        """The MQTT port defaults to 1883."""
        assert build_payload("MyWiFi", "s3cret-pass!", "192.168.178.2") == PAYLOAD

    @pytest.mark.parametrize(
        ("ssid", "password", "ip", "port", "match"),
        [
            ("", "pw", "192.168.1.1", 1883, "SSID must not be empty"),
            ("x" * 33, "pw", "192.168.1.1", 1883, "must not exceed 32"),
            ("Café", "pw", "192.168.1.1", 1883, "SSID must consist of printable ASCII"),
            ("ssid", "pässword", "192.168.1.1", 1883, "password must consist of"),
            ("tab\there", "pw", "192.168.1.1", 1883, "SSID must consist of"),
            ("my,net", "pw", "192.168.1.1", 1883, "SSID must not contain a comma"),
            ("ssid", "a,b", "192.168.1.1", 1883, "password must not contain a comma"),
            ("ssid", "pw", "broker.local", 1883, "is not an IPv4 address"),
            ("ssid", "pw", "fe80::1", 1883, "is not an IPv4 address"),
            ("ssid", "pw", "192.168.1.256", 1883, "is not an IPv4 address"),
            ("ssid", "pw", "0.0.0.0", 1883, "cloud"),  # noqa: S104
            ("ssid", "pw", "192.168.1.1", 0, "between 1 and 65535"),
            ("ssid", "pw", "192.168.1.1", 65536, "between 1 and 65535"),
        ],
    )
    def test_rejected(
        self, ssid: str, password: str, ip: str, port: int, match: str
    ) -> None:
        """Values the message cannot carry are rejected with a clear reason."""
        with pytest.raises(InvalidSettingsError, match=match):
            build_payload(ssid, password, ip, port)

    def test_rejection_is_a_value_error(self) -> None:
        """Callers catching ValueError keep working."""
        with pytest.raises(ValueError, match="IPv4"):
            build_payload("ssid", "pw", "nope", 1883)


class TestSendPayload:
    """Tests for delivering the message."""

    def test_sends_to_the_hotspot_address(self, fake_socket: MagicMock) -> None:
        """The default target is the thermostat inside its hotspot."""
        send_payload(PAYLOAD)

        fake_socket.create_connection.assert_called_once_with(
            THERMOSTAT_ADDRESS, timeout=2.0
        )
        fake_socket.sendall.assert_called_once_with(PAYLOAD)
        fake_socket.__exit__.assert_called_once()

    def test_custom_target(self, fake_socket: MagicMock) -> None:
        """Address and port of the thermostat can be overridden."""
        send_payload(PAYLOAD, ("192.168.4.1", 5000))

        fake_socket.create_connection.assert_called_once_with(
            ("192.168.4.1", 5000), timeout=2.0
        )

    @pytest.mark.parametrize(
        "error",
        [TimeoutError("timed out"), ConnectionRefusedError(), socket.gaierror()],
    )
    def test_connect_failure(self, fake_socket: MagicMock, error: OSError) -> None:
        """A failed connection is reported with a hint about the hotspot."""
        fake_socket.create_connection.side_effect = error

        with pytest.raises(ThermostatUnreachableError, match="hotspot") as info:
            send_payload(PAYLOAD)

        assert info.value.__cause__ is error
        fake_socket.sendall.assert_not_called()

    def test_send_failure(self, fake_socket: MagicMock) -> None:
        """A failed send is reported and the socket is closed."""
        fake_socket.sendall.side_effect = BrokenPipeError()

        with pytest.raises(ThermostatUnreachableError, match="hotspot"):
            send_payload(PAYLOAD)

        fake_socket.__exit__.assert_called_once()

    def test_unreachable_is_a_connection_error(self, fake_socket: MagicMock) -> None:
        """Callers catching ConnectionError keep working."""
        fake_socket.create_connection.side_effect = TimeoutError()

        with pytest.raises(ConnectionError):
            send_payload(PAYLOAD)


class TestProvision:
    """Tests for the one-call entry point."""

    def test_encodes_and_sends(self, fake_socket: MagicMock) -> None:
        """The arguments are encoded and delivered to the thermostat."""
        provision("MyWiFi", "s3cret-pass!", "192.168.178.2")

        fake_socket.create_connection.assert_called_once_with(
            THERMOSTAT_ADDRESS, timeout=2.0
        )
        fake_socket.sendall.assert_called_once_with(PAYLOAD)

    def test_custom_thermostat_target(self, fake_socket: MagicMock) -> None:
        """The thermostat address is passed through."""
        provision(
            "MyWiFi",
            "s3cret-pass!",
            "192.168.178.2",
            8883,
            thermostat_address=("192.168.4.1", 5000),
        )

        fake_socket.create_connection.assert_called_once_with(
            ("192.168.4.1", 5000), timeout=2.0
        )

    def test_invalid_settings_send_nothing(self, fake_socket: MagicMock) -> None:
        """Validation happens before any connection is attempted."""
        with pytest.raises(InvalidSettingsError):
            provision("MyWiFi", "pw", "broker.local")

        fake_socket.create_connection.assert_not_called()
