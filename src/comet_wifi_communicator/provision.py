"""Provisioning of a Comet WiFi thermostat over its setup hotspot.

After a factory reset the thermostat opens the Wi-Fi hotspot ``Comet Wifi``
and listens on a TCP port for a configuration message. The message names
the Wi-Fi network the thermostat should join and the MQTT broker it should
talk to.
"""

import ipaddress
import logging
import socket
import time

_LOGGER = logging.getLogger(__name__)

THERMOSTAT_IP = "10.0.0.1"
"""Address of the thermostat inside its setup hotspot."""

THERMOSTAT_PORT = 1233
"""TCP port the thermostat listens on for the configuration message."""

THERMOSTAT_ADDRESS = (THERMOSTAT_IP, THERMOSTAT_PORT)

DEFAULT_MQTT_PORT = 1883

CONNECT_TIMEOUT = 2.0
"""Seconds to wait for the TCP connection and for the send to complete."""

SEND_GRACE = 2.0
"""Seconds to keep the connection open after sending.

Closing right away may lead to dropping the message.
"""

_SEPARATOR = ","
# Placeholders for the cloud credentials. The firmware only reads them when
# the broker address is 0.0.0.0, which selects the manufacturer's cloud.
_CLOUD_USER = "00000000"
_CLOUD_PASSWORD = "0000000000000000"  # noqa: S105  # nosec B105

_MAX_SSID_LENGTH = 32
_MAX_PORT = 65535


class ProvisioningError(Exception):
    """Base class for every error raised by this module."""


class InvalidSettingsError(ProvisioningError, ValueError):
    """A setting cannot be sent to the thermostat.

    Also, a :class:`ValueError`, so callers that already catch that keep
    working.
    """


class ThermostatUnreachableError(ProvisioningError, ConnectionError):
    """The thermostat's setup hotspot did not accept the configuration."""


def _validate_text(value: str, name: str) -> None:
    """Reject text the setup message cannot contain.

    :param value: The text to check.
    :param name: How to call it in the error message.
    :raises InvalidSettingsError: If the text is not printable ASCII or
        contains the field separator.
    """
    if not value.isascii() or not value.isprintable():
        msg = f"The {name} must consist of printable ASCII characters only."
        raise InvalidSettingsError(msg)
    if _SEPARATOR in value:
        msg = f"The {name} must not contain a comma."
        raise InvalidSettingsError(msg)


def _validate_broker_ip(mqtt_server_ip: str) -> ipaddress.IPv4Address:
    """Parse the broker address.

    :param mqtt_server_ip: The address as typed by the user.
    :return: The parsed address.
    :raises InvalidSettingsError: If it is not a usable IPv4 address.
    """
    try:
        ip = ipaddress.IPv4Address(mqtt_server_ip)
    except ipaddress.AddressValueError as err:
        msg = (
            f"{mqtt_server_ip!r} is not an IPv4 address. The thermostat cannot "
            "resolve host names and does not support IPv6."
        )
        raise InvalidSettingsError(msg) from err
    if ip.is_unspecified:
        msg = "0.0.0.0 would send the thermostat to the manufacturer's cloud."
        raise InvalidSettingsError(msg)
    return ip


def build_payload(
    wifi_ssid: str,
    wifi_password: str,
    mqtt_server_ip: str,
    mqtt_server_port: int = DEFAULT_MQTT_PORT,
) -> bytes:
    """Encode the configuration message.

    :param wifi_ssid: The Wi-Fi network the thermostat should join.
    :param wifi_password: Its password, empty for an open network.
    :param mqtt_server_ip: IPv4 address of the MQTT broker.
    :param mqtt_server_port: TCP port of the MQTT broker.
    :return: The message as sent over the socket.
    :raises InvalidSettingsError: If a value cannot be encoded.
    """
    if not wifi_ssid:
        msg = "The Wi-Fi SSID must not be empty."
        raise InvalidSettingsError(msg)
    if len(wifi_ssid) > _MAX_SSID_LENGTH:
        msg = f"The Wi-Fi SSID must not exceed {_MAX_SSID_LENGTH} characters."
        raise InvalidSettingsError(msg)
    _validate_text(wifi_ssid, "Wi-Fi SSID")
    _validate_text(wifi_password, "Wi-Fi password")
    ip = _validate_broker_ip(mqtt_server_ip)
    if not 1 <= mqtt_server_port <= _MAX_PORT:
        msg = f"The MQTT port must be between 1 and {_MAX_PORT}."
        raise InvalidSettingsError(msg)

    # The Wi-Fi credentials form one hex field including the separator. The
    # firmware splits it after decoding. The remaining fields are plain text.
    wifi_field = f"{wifi_ssid}{_SEPARATOR}{wifi_password}".encode("ascii").hex()
    fields = (
        wifi_field,
        _CLOUD_USER,
        _CLOUD_PASSWORD,
        f"{int(ip):08X}",
        f"{mqtt_server_port:04X}",
    )
    return _SEPARATOR.join(fields).upper().encode("ascii")


def send_payload(
    payload: bytes, thermostat_address: tuple[str, int] = THERMOSTAT_ADDRESS
) -> None:
    """Deliver an encoded configuration message to the thermostat.

    The caller must be connected to the thermostat's setup hotspot.

    :param payload: The message from :func:`build_payload`.
    :param thermostat_address: Host and port where the thermostat listens.
    :raises ThermostatUnreachableError: If the connection or the send fails.
    """
    host, port = thermostat_address
    _LOGGER.info("Connecting to the thermostat at %s:%d.", host, port)
    try:
        with socket.create_connection(
            thermostat_address, timeout=CONNECT_TIMEOUT
        ) as sock:
            _LOGGER.info("Connected, sending the configuration.")
            sock.sendall(payload)
            time.sleep(SEND_GRACE)
    except OSError as err:
        msg = (
            f"Could not deliver the configuration to {host}:{port} ({err}). "
            "Is this computer connected to the thermostat's hotspot?"
        )
        raise ThermostatUnreachableError(msg) from err
    _LOGGER.info("Configuration sent.")


def provision(
    wifi_ssid: str,
    wifi_password: str,
    mqtt_server_ip: str,
    mqtt_server_port: int = DEFAULT_MQTT_PORT,
    *,
    thermostat_address: tuple[str, int] = THERMOSTAT_ADDRESS,
) -> None:
    """Point a thermostat in setup mode at a Wi-Fi network and an MQTT broker.

    :param wifi_ssid: The Wi-Fi network the thermostat should join.
    :param wifi_password: Its password, empty for an open network.
    :param mqtt_server_ip: IPv4 address of the MQTT broker.
    :param mqtt_server_port: TCP port of the MQTT broker.
    :param thermostat_address: Host and port where the thermostat listens.
    :raises InvalidSettingsError: If a value cannot be encoded.
    :raises ThermostatUnreachableError: If the connection or the send fails.
    """
    payload = build_payload(wifi_ssid, wifi_password, mqtt_server_ip, mqtt_server_port)
    _LOGGER.info(
        "Configuring Wi-Fi %r and MQTT broker %s:%d.",
        wifi_ssid,
        mqtt_server_ip,
        mqtt_server_port,
    )
    send_payload(payload, thermostat_address)
