import re


def convert_temperature_to_float(hex_value: str) -> float:
    decimal = convert_hex_to_int(hex_value)
    return decimal / 2.0


def convert_temperature_to_hex(decimal: float) -> str:
    decimal = int(decimal * 2.0) # @TODO: Describe how this deals with decimals different to .5
    hex_value = hex(decimal)[2:]  # Remove 0x prefix
    return f"#{hex_value.upper()}"


def convert_hex_to_int(hex_value: str) -> int:
    hex_value = hex_value.lstrip("#")
    return int(hex_value, 16)


def validate_and_streamline_mac(mac: str) -> str:
    mac_address_regex = re.compile(r'^([0-9a-fA-F]{2}[:-]?){5}([0-9a-fA-F]{2})$|^[0-9a-fA-F]{12}$')
    if not mac_address_regex.match(mac):
        raise ValueError(f"Invalid MAC address: {mac}")
    return mac.replace(":", "").replace("-", "").upper()

