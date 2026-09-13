"""Test helper functions."""

import pytest

from comet_wifi_communicator.helper import (
    char_to_unicode,
    string_to_unicode,
    int_to_hex_str,
    ip_to_hex_str,
    IPv6NotAllowed,
)

class TestIntToHexStr:
    """Tests for int_to_hex_str helper."""

    @pytest.mark.parametrize("number,expected", [
        (0, "0"),
        (1, "1"),
        (10, "a"),
        (15, "f"),
        (16, "10"),
        (255, "ff"),
        (256, "100"),
        (4095, "fff"),
        (65535, "ffff"),
    ])
    def test_int_to_hex_str(self, number, expected):
        """Convert various integers to hex string."""
        assert int_to_hex_str(number) == expected

    def test_uppercase_flag_true(self):
        """Uppercase flag should convert hex letters to uppercase."""
        result = int_to_hex_str(255, uppercase=True)
        assert result == "FF"

    def test_uppercase_flag_false(self):
        """Uppercase flag false should keep lowercase hex."""
        result = int_to_hex_str(255, uppercase=False)
        assert result == "ff"

    def test_uppercase_default_is_false(self):
        """Uppercase parameter defaults to False."""
        result = int_to_hex_str(255)
        assert result == result.lower()

    def test_return_type_is_string(self):
        """Result should always be a string."""
        result = int_to_hex_str(255)
        assert isinstance(result, str)

    def test_negative_number(self):
        """Negative numbers should raise ValueError."""
        with pytest.raises(ValueError):
            int_to_hex_str(-1)


class TestCharToUnicode:
    """Test function for char_to_unicode helper."""

    @pytest.mark.parametrize("char,expected", [
        ("A", "41"),
        ("a", "61"),
        ("0", "30"),
        (" ", "20"),
        ("!", "21"),
        ("€", "20ac"),
        ("\n", "a"),
        ("\t", "9"),
    ])
    def test_char_to_unicode(self, char, expected):
        """Convert various characters to Unicode hex."""
        assert char_to_unicode(char) == expected

    def test_return_type_is_string(self):
        """Result should always be a string."""
        result = char_to_unicode("A")
        assert isinstance(result, str)

    def test_lowercase_hex_output(self):
        """Hex output should be lowercase."""
        result = char_to_unicode("A")
        assert result == result.lower()

    def test_null_character(self):
        """Null character should return '0'."""
        assert char_to_unicode("\x00") == "0"

    def test_multi_char_input(self):
        """Multi-char raises exception."""
        with pytest.raises(ValueError):
            char_to_unicode("ABC")

    def test_empty_string_raises_error(self):
        """Empty string should raise ValueError on empty."""
        with pytest.raises(ValueError):
            char_to_unicode("")


class TestStringToUnicode:
    """Tests for string_to_unicode helper."""

    @pytest.mark.parametrize("string,expected", [
        ("A", "41"),
        ("AB", "4142"),
        ("Hello", "48656c6c6f"),
        ("123", "313233"),
        ("", "")
    ])
    def test_string_to_unicode(self, string, expected):
        """Convert various strings to Unicode hex."""
        assert string_to_unicode(string) == expected

    def test_uppercase_flag_true(self):
        """Uppercase flag should convert hex letters to uppercase."""
        result = string_to_unicode("café", uppercase=True)
        assert result == result.upper()
        assert "E9" in result  # é in hex

    def test_uppercase_flag_false(self):
        """Uppercase flag false should keep lowercase hex."""
        result = string_to_unicode("café", uppercase=False)
        assert result == result.lower()

    def test_uppercase_default_is_false(self):
        """Uppercase parameter defaults to False."""
        result = string_to_unicode("café")
        assert result == result.lower()

    def test_return_type_is_string(self):
        """Result should always be a string."""
        result = string_to_unicode("A")
        assert isinstance(result, str)

class TestIpToHexStr:
    """Tests for ip_to_hex_string helper."""

    @pytest.mark.parametrize("ip,ip_hex", [
            ("192.168.0.2", "c0a80002"),
            ("127.0.0.1", "7f000001"),
            ("0.0.0.0", "00000000"),
            ("255.255.255.255", "ffffffff"),
            ("10.0.0.1", "0a000001"),
            ("172.16.0.1", "ac100001"),
            ("1.1.1.1", "01010101"),
            ("8.8.8.8", "08080808"),
    ])
    def test_valid_ipv4_lowercase(self, ip, ip_hex):
        """Test valid IPv4 addresses with lowercase output (default)."""
        assert ip_to_hex_str(ip) == ip_hex

    @pytest.mark.parametrize("ip,ip_hex", [
            ("192.168.0.2", "C0A80002"),
            ("127.0.0.1", "7F000001"),
            ("0.0.0.0", "00000000"),
            ("255.255.255.255", "FFFFFFFF"),
            ("10.0.0.1", "0A000001"),
            ("172.16.0.1", "AC100001"),
            ("1.1.1.1", "01010101"),
            ("8.8.8.8", "08080808"),
        ])
    def test_valid_ipv4_uppercase(self, ip, ip_hex):
        """Test valid IPv4 addresses with uppercase output."""
        assert ip_to_hex_str(ip, uppercase=True) == ip_hex

    @pytest.mark.parametrize("invalid_ip", [
            "256.1.1.1",  # Octet out of range
            "192.168.1",  # Missing octet
            "192.168.1.1.1",  # Extra octet
            "not.an.ip.address",  # Non-numeric
            "192.168.a.1",  # Non-numeric octet
            "",  # Empty string
            "192.168.-1.1",  # Negative octet
            "192.168.1.256",  # Out of range
            "192.168.1.1.1.1",  # Too many segments
            "192.168..1",  # Missing segment
            "....",  # Only dots
            "192 168 1 1",  # Spaces instead of dots
            "192.168.1.1/24",  # CIDR notation (not plain IP)
        ])
    def test_invalid_ipv4_format(self, invalid_ip):
        """Test that invalid IPv4 formats raise ValueError."""
        with pytest.raises(ValueError):
            ip_to_hex_str(invalid_ip)

    @pytest.mark.parametrize("ipv6", [
            "2001:db8::1",
            "::1",
            "fe80::1",
            "::",
            "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            "ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff",
        ])
    def test_ipv6_input(self, ipv6):
        """Test that IPv6 addresses raise IPv6NotAllowed."""
        with pytest.raises(IPv6NotAllowed):
            ip_to_hex_str(ipv6)

    def test_uppercase_false_default(self):
        """Test that uppercase=False is the default behavior."""
        ip = "192.168.1.1"
        assert ip_to_hex_str(ip) == ip_to_hex_str(ip, uppercase=False)
