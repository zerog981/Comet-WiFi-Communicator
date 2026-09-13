"""Helper functions."""
import ipaddress


def int_to_hex_str(number: int, uppercase=False) -> str:
    """
    Converts an non-negative integer into a string in its hexadecimal representation.
    :param number: Input integer.
    :param uppercase: Convert output letters to uppercase.
    :return:
    """
    if number < 0:
        raise ValueError
    output = format(number, "x")
    if uppercase:
        return output.upper()
    return output

def char_to_unicode(char: str) -> str:
    """
    Convert a character to its Unicode hex representation.
    :param char: Single character.
    
    :return: Unicode Hex string.
    :raises ValueError: If multi-character is supplied.
    """
    if len(char) != 1:
        raise ValueError(f"Expected a single character, got {char}.")
    return f"{ord(char):x}"


def string_to_unicode(string: str, uppercase=False) -> str:
    """
    Convert a string to its Unicode hex representation.
    :param string: Input string.
    :param uppercase: Convert output letters to uppercase.

    :return: Output Unicode hex representation string.
    """
    output = ""
    for char in string:
        output += char_to_unicode(char)
    if uppercase:
        return output.upper()
    return output


def ip_to_hex_str(ip_str: str, uppercase=False) -> str:
    """
    Converts an IP string into its hex representation.
    :param ip_str: IP address in string format, e.g. "192.168.0.2".
    :param uppercase: Convert output letters to uppercase.
    :return: String of IP in hex representation, e.g. "C0A80002".
    """
    ip = ipaddress.ip_address(ip_str) # Validate IP
    if ip.version == 6:
        raise IPv6NotAllowed("Supplied IP has IPv6 format. Not supported.")
    ip_hex = ip.packed.hex()
    if uppercase:
        return ip_hex.upper()
    return ip_hex


class IPv6NotAllowed(Exception):
    """Exception for unsupported IPv6."""
    pass