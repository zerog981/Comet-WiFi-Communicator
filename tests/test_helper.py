"""Test helper functions."""

import pytest

from comet_wifi_communicator.helper import (
    decode_temperature,
    convert_hex_str_to_int,
    encode_temperature,
)


class TestDecodeTemperature:
    """Tests for decoding temperature from thermostats."""

    @pytest.mark.parametrize("hex_input,expected_temperature", [
        ("10", 8),
        ("1F", 15.5),
        ("38", 28),
    ])
    def test_basic(self, hex_input, expected_temperature):
        """Test basic functionality"""
        assert decode_temperature(hex_input) == expected_temperature

    def test_non_uppercase(self):
        """Lowercase hex input."""
        assert decode_temperature("1f") == 15.5

    @pytest.mark.parametrize("hex_input", [
        "GG",
        "1G",
        "",
    ])
    def test_invalid(self, hex_input):
        """Invalid hex characters should raise ValueError."""
        with pytest.raises(ValueError):
            decode_temperature(hex_input)

    @pytest.mark.parametrize("hex_input", [
        None,
        27,
    ])
    def test_invalid_type(self, hex_input):
        """Invalid input should raise TypeError."""
        with pytest.raises(TypeError):
            decode_temperature(hex_input)


class TestEncodeTemperature:
    """Tests for encoding temperature for thermostats."""

    @pytest.mark.parametrize(
        "temperature,expected",
        [
            (8, 0x10),
            (15.5, 0x1F),
            (28, 0x38),
            (15.6, 0x1F),  # Cut decimals, if not .5
            (15.9, 0x1F),  # Cut decimals, if not .5
        ],
    )
    def test_basic(self, temperature, expected):
        """Test basic functionality"""
        assert encode_temperature(temperature) == expected

    def test_negative(self):
        """Lowercase hex input."""
        with pytest.raises(ValueError):
            encode_temperature(-10)

    @pytest.mark.parametrize("input", [
        None,
        "27",
    ])
    def test_invalid_type(self, input):
        """Invalid input should raise TypeError."""
        with pytest.raises(TypeError):
            encode_temperature(input)


class TestConvertHexStrToInt:
    """Tests for helper functions."""

    @pytest.mark.parametrize("hex_input,expected", [
        ("1B", 27),
        ("00", 0),
        ("FF", 255),
    ])
    def test_basic(self, hex_input, expected):
        """Basic hex input."""
        assert convert_hex_str_to_int(hex_input) == expected

    @pytest.mark.parametrize("hex_input,expected", [
        ("1b", 27),
        ("Ff", 255)
    ])
    def test_non_uppercase(self, hex_input, expected):
        """Lowercase hex input."""
        assert convert_hex_str_to_int(hex_input) == expected

    @pytest.mark.parametrize("hex_input", [
        "GG",
        "1G",
        "",
    ])
    def test_invalid_hex(self, hex_input):
        """Invalid hex characters should raise ValueError."""
        with pytest.raises(ValueError):
            convert_hex_str_to_int(hex_input)

    @pytest.mark.parametrize("hex_input", [
        None,
        27,
    ])
    def test_invalid_type(self, hex_input):
        """Invalid input should raise TypeError."""
        with pytest.raises(TypeError):
            convert_hex_str_to_int(hex_input)

