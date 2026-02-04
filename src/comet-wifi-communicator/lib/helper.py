def convert_temperature_to_float(hex_value: str) -> float:
    decimal = convert_hex_to_int(hex_value)
    return decimal / 2.0


def convert_temperature_to_hex(decimal: float) -> str:
    decimal = int(decimal * 2.0)
    hex_value = hex(decimal)[2:]  # Remove 0x prefix
    return f"#{hex_value.upper()}"


def convert_hex_to_int(hex_value: str) -> int:
    hex_value = hex_value.lstrip("#")
    return int(hex_value, 16)