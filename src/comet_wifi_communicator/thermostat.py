"""Thermostat communication class."""

import time
from dataclasses import dataclass

from paho.mqtt.client import CONNACK_ACCEPTED, Client
from paho.mqtt.enums import CallbackAPIVersion

from comet_wifi_communicator import const
from comet_wifi_communicator.const import (
    CONNECTION_TEST_TIMEOUT,
    HEX_PREFIX,
    REQUEST_BASE_SOFTWARE_VERSION,
    REQUEST_BATTERY,
    REQUEST_CONFIG,
    REQUEST_DATETIME,
    REQUEST_TEMPERATURE_AMBIENT,
    REQUEST_TEMPERATURE_OFFSET,
    REQUEST_TEMPERATURE_SETPOINT,
    REQUEST_WIFI_SIGNAL_STRENGTH,
    REQUEST_WIFI_SOFTWARE_VERSION,
    REQUEST_WINDOW_OPEN_CONFIG,
    TEMPERATURE_HEX_OFF,
    TEMPERATURE_HEX_ON,
    TEMPERATURE_SETPOINT_MAX,
    TEMPERATURE_SETPOINT_MIN,
    CFG_PAYLOAD_LENGTH,
    CFG_KEY_LOCK_PLUS,
    CFG_KEY_LOCK,
    CFG_MIRRORED_DISPLAY,
    CFG_DST,
)
from comet_wifi_communicator.helper import (
    convert_hex_to_int,
    convert_temperature_to_float,
    convert_temperature_to_hex,
    validate_and_streamline_mac,
)
from comet_wifi_communicator.mqtt_topics import MqttTopics


@dataclass
class ThermostatData:
    """Holds data for thermostat."""
    temperature_setpoint: float = 0.0
    temperature_ambient: float = 0.0
    temperature_offset: float = 0.0
    window_open: bool = False
    battery_level: float = 0.0
    is_heating: bool = False

@dataclass
class ThermostatConfig:
    """Class for holding thermostat configuration."""
    _key_lock: bool = False
    _key_lock_plus: bool = False
    _display_mirrored: bool = False
    _dst: bool = False

    @property
    def key_lock(self) -> bool:
        """Return key lock status."""
        return self._key_lock

    @property
    def key_lock_plus(self) -> bool:
        """Return key lock plus status."""
        return self._key_lock_plus

    @property
    def display_mirrored(self) -> bool:
        """Return display mirrored status."""
        return self._display_mirrored

    @property
    def dst(self) -> bool:
        """Return daylight savings time (DST) status."""
        return self._dst

    def write_config(self, config_byte: int) -> None:
        """
        Update configuration based on configuration byte received from thermostat.
        :param config_byte: Configuration byte as received from thermostat. Bit 0 is DST, Bit 1 is Mirrored Display, Bit 2 is Key Lock, and Bit 3 is Key Lock Plus.
        """
        if config_byte < 0:
            raise ValueError("Invalid configuration byte.")
        self._key_lock_plus = bool(config_byte & CFG_KEY_LOCK_PLUS)
        self._key_lock = bool(config_byte & CFG_KEY_LOCK)
        self._display_mirrored = bool(config_byte & CFG_MIRRORED_DISPLAY)
        self._dst = bool(config_byte & CFG_DST)


class Thermostat:
    """
    Thermostat communication class.
    """
    def __init__(self, mqtt_host: str, mqtt_port: int, mac: str):
        self._mac = validate_and_streamline_mac(mac)
        self._mqtt_host = mqtt_host
        self._mqtt_port = mqtt_port
        self._connected = False
        self._topics = MqttTopics(self._mac)
        self._data = ThermostatData()
        self.config = ThermostatConfig()

        self._mqtt_client = Client(callback_api_version=CallbackAPIVersion.VERSION2)
        self._mqtt_client.on_connect = self._on_mqtt_connect
        self._mqtt_client.on_message = self._on_mqtt_message

        self._mqtt_client.user_data_set([])  # Clear user data from the client

        self._last_connection_test_published = 0

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def mqtt_host(self) -> str:
        return self._mqtt_host

    @property
    def setpoint(self) -> float:
        return self._data.temperature_setpoint

    @property
    def temperature_ambient(self) -> float:
        return self._data.temperature_ambient

    @property
    def temperature_offset(self) -> float:
        return self._data.temperature_offset

    @property
    def is_heating(self) -> bool:
        return self._data.is_heating

    @property
    def window_open(self) -> bool:
        return self._data.window_open

    @property
    def battery_level(self) -> float:
        return self._data.battery_level

    @property
    def mac(self) -> str:
        return self._mac

    def _on_mqtt_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code is not CONNACK_ACCEPTED.value:
            raise MQTTConnectError
        # Subscribe from on_connect to be sure that subscription is persisted across reconnections
        for topic in self._topics.reply_topics.values():
            client.subscribe(topic)
        client.subscribe(self._topics.command_topics["CONNECTION_TEST"])

    def _on_mqtt_message(self, client, userdata, message):

        # Thermostat disconnected
        if message.topic == self._topics.reply_topics["WILL"]:
            self._connected = False
            return

        self._connected = True
        if message.topic == self._topics.command_topics["CONNECTION_TEST"]:
            if time.time() - self._last_connection_test_published > CONNECTION_TEST_TIMEOUT:
                self._publish_connection_test()
            return

        if message.topic == self._topics.reply_topics["TEMPERATURE_AMBIENT"]:
            self._data.temperature_ambient = convert_temperature_to_float(
                message.payload.decode("utf-8")
            )
            return

        if message.topic == self._topics.reply_topics["TEMPERATURE_SETPOINT"]:
            payload = message.payload.decode("utf-8")
            if payload == f"{HEX_PREFIX}{TEMPERATURE_HEX_OFF:02X}":
                self._data.is_heating = False
                self._data.temperature_setpoint = TEMPERATURE_SETPOINT_MIN
                return
            if payload == f"{HEX_PREFIX}{TEMPERATURE_HEX_ON:02X}":
                self._data.temperature_setpoint = TEMPERATURE_SETPOINT_MAX
            else:
                self._data.temperature_setpoint = convert_temperature_to_float(
                    payload
                )
            self._data.is_heating = True
            return

        if message.topic == self._topics.reply_topics["BATTERY"]:
            self._data.battery_level = convert_hex_to_int(
                message.payload.decode("utf-8")
            )
            return

        if message.topic == self._topics.reply_topics["CONFIGURATION"]:
            payload = message.payload.decode("utf-8")
            raw_data = int(payload.lstrip(HEX_PREFIX), 16)
            config_byte = raw_data >> 8 & 0xFF
            self.config.write_config(config_byte)
            return

    def _publish_connection_test(self):
        self._mqtt_client.publish(
            self._topics.command_topics["CONNECTION_TEST"], const.CONNECTION_TEST_COMMAND
        )
        self._last_connection_test_published = time.time()

    async def connect(self) -> None:
        """Initiate connection to MQTT broker.

        Initiates connection to MQTT broker and requests all standard parameters from thermostat.

        """
        self._mqtt_client.connect(self._mqtt_host, self._mqtt_port)
        self._mqtt_client.loop_start()
        await self.update_standard_values()

    async def disconnect(self):
        """Disconnect from MQTT broker.

        Disconnect from MQTT broker.

        """
        self._mqtt_client.disconnect()
        self._mqtt_client.loop_stop()
        self._connected = False

    async def update_values(self, request_value: int = 0xFFFFFFFF) -> None:
        """Update all parameters.

        Use this function to fetch setpoint temperature, ambient temperature, battery level,
        configuration parameters, open window settings etc. Supply the constants in the form REQUEST_TEMPERATURE_SETPOINT | REQUEST_TEMPERATURE_AMBIENT | REQUEST_WIFI_SIGNAL_STRENGTH

        :return: None
        """
        request_str = f"{HEX_PREFIX}{request_value:08X}"
        self._mqtt_client.publish(
            self._topics.command_topics["GENERAL_VALUE_REQUEST"], request_str
        )

    async def update_standard_values(self):
        await self.update_values(
            REQUEST_TEMPERATURE_SETPOINT
            | REQUEST_TEMPERATURE_AMBIENT
            | REQUEST_TEMPERATURE_OFFSET
            | REQUEST_CONFIG
            | REQUEST_DATETIME
            | REQUEST_WINDOW_OPEN_CONFIG
            | REQUEST_BATTERY
            | REQUEST_BASE_SOFTWARE_VERSION
            | REQUEST_WIFI_SOFTWARE_VERSION
            | REQUEST_WIFI_SIGNAL_STRENGTH
        )

    async def update_heating_values(self):
        await self.update_values(
            REQUEST_TEMPERATURE_SETPOINT
            | REQUEST_TEMPERATURE_AMBIENT
            | REQUEST_TEMPERATURE_OFFSET
        )  # TODO: Add window open

    async def update_config(self):
        await self.update_values(REQUEST_CONFIG)

    async def _config_enable(self, values: int = 0x0000):
        if not self._connected:
            raise ConnectionError()
        # Payload has five bytes with first byte containing enable flags
        config_payload = f"{HEX_PREFIX}{values:02X}{'0' * ((CFG_PAYLOAD_LENGTH - 1) * 2)}"
        self._mqtt_client.publish(
            self._topics.command_topics["WRITE_CONFIGURATION"], config_payload
        )
        await self.update_config()
        
    async def _config_disable(self, values: int = 0x0000):
        if not self._connected:
            raise ConnectionError()
        # Payload has five bytes with second byte containing disable flags
        config_payload = f"{HEX_PREFIX}{'0' * 2}{values:02X}{'0' * ((CFG_PAYLOAD_LENGTH - 2) * 2)}"
        self._mqtt_client.publish(
            self._topics.command_topics["WRITE_CONFIGURATION"], config_payload
        )
        await self.update_config()
        
    async def enable_key_lock_plus(self):
        await self._config_enable(CFG_KEY_LOCK_PLUS)
        
    async def disable_key_lock_plus(self):
        await self._config_disable(CFG_KEY_LOCK_PLUS)
        
    async def enable_key_lock(self):
        await self._config_enable(CFG_KEY_LOCK)
    
    async def disable_key_lock(self):
        await self._config_disable(CFG_KEY_LOCK)
        
    async def enable_mirrored_display(self):
        await self._config_enable(CFG_MIRRORED_DISPLAY)
    
    async def disable_mirrored_display(self):
        await self._config_disable(CFG_MIRRORED_DISPLAY)
        
    async def enable_dst(self):
        await self._config_enable(CFG_DST)
    
    async def disable_dst(self):
        await self._config_disable(CFG_DST)

    async def set_temperature(self, temperature: float) -> None:
        if not self._connected:
            raise ConnectionError()
        if temperature > TEMPERATURE_SETPOINT_MAX:
            temperature = TEMPERATURE_SETPOINT_MAX
        if temperature < TEMPERATURE_SETPOINT_MIN:
            temperature = TEMPERATURE_SETPOINT_MIN
        temperature_encoded = convert_temperature_to_hex(temperature)
        self._mqtt_client.publish(
            self._topics.command_topics["WRITE_TEMPERATURE_SETPOINT"],
            temperature_encoded,
        )
        await self.update_heating_values()

    async def turn_off(self) -> None:
        if not self._connected:
            raise ConnectionError()
        self._mqtt_client.publish(
            self._topics.command_topics["WRITE_TEMPERATURE_SETPOINT"],
            f"{HEX_PREFIX}{TEMPERATURE_HEX_OFF:02X}",
        )
        await self.update_heating_values()

    async def turn_fully_on(self) -> None:
        if not self._connected:
            raise ConnectionError()
        self._mqtt_client.publish(
            self._topics.command_topics["WRITE_TEMPERATURE_SETPOINT"],
            f"{HEX_PREFIX}{TEMPERATURE_HEX_ON:02X}",
        )
        await self.update_heating_values()


class MQTTConnectError(Exception):
    pass
