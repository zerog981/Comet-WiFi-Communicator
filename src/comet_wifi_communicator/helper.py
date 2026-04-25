"""Helper functions."""

import re

from comet_wifi_communicator.const import HEX_PREFIX


def convert_temperature_to_float(hex_value: str) -> float:
    """
    Convert a hex temperature value to float.
    :param hex_value: Input temperature raw hex value including "#", e.g. "#1B".
    :return: Temperature value as decimal number, e.g. 13.5.
    """
    decimal = convert_hex_to_int(hex_value)
    return decimal / 2.0


def convert_temperature_to_hex(decimal: float) -> str:
    """
    Convert a temperature value to a raw hex value.
    :param decimal: Input temperature value, e.g. 13.5.
    :return: Temperature value as hex string including "#", e.g. "#1B".
    """
    decimal_int = int(decimal * 2.0) # If supplied value is different to .0 or .5, decimals will be cut after doubling
    hex_value = hex(decimal_int)[2:]  # Remove 0x prefix
    return f"{HEX_PREFIX}{hex_value.upper()}"


def convert_hex_to_int(hex_value: str) -> int:
    """
    Convert a hex value to int.
    :param hex_value: Raw hex value including "#", e.g. "#1B".
    :return: Integer value as decimal number, e.g. 27.
    """
    hex_value = hex_value.lstrip(HEX_PREFIX)
    return int(hex_value, 16)


def validate_and_streamline_mac(mac: str) -> str:
    """
    Validate and convert a MAC address to a common format.
    :param mac: Input MAC address as string, either delimited by ":" or "-", or as numbers only.
    :return: Streamlined MAC address as string, e.g., AABBCCDDEE.
    :raises: ValueError if MAC address is not valid.
    """
    mac_address_regex = re.compile(r'^([0-9a-fA-F]{2}[:-]?){5}([0-9a-fA-F]{2})$|^[0-9a-fA-F]{12}$')
    if not mac_address_regex.match(mac):
        raise ValueError(f"Invalid MAC address: {mac}")
    return mac.replace(":", "").replace("-", "").upper()

