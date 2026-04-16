"""Test ThermostatConfig dataclass."""

from src.comet_wifi_communicator.thermostat import ThermostatConfig


class TestThermostatConfig:
    """Test ThermostatConfig dataclass."""

    def test_config_default_values(self):
        """Config initializes with all False values."""
        config = ThermostatConfig()
        assert config.key_lock is False
        assert config.key_lock_plus is False
        assert config.display_mirrored is False
        assert config.dst is False

    def test_config_setters(self):
        """Config setters work correctly."""
        config = ThermostatConfig()
        config.key_lock = True
        config.dst = True

        assert config.key_lock is True
        assert config.dst is True
