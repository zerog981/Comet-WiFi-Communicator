"""Thermostat communication class."""

import time
from dataclasses import dataclass

from paho.mqtt.client import CONNACK_ACCEPTED, Client

from . import const
from src.comet_wifi_communicator.const import (
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
)
from src.comet_wifi_communicator.helper import (
    convert_hex_to_int,
    convert_temperature_to_float,
    convert_temperature_to_hex,
    validate_and_streamline_mac,
)
from src.comet_wifi_communicator.mqtt_topics import MqttTopics


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

    _hex_string: str = "#0000"

    @property
    def key_lock(self) -> bool:
        """Return key lock status."""
        return self._key_lock

    @key_lock.setter
    def key_lock(self, value: bool) -> None:
        """Set key lock status."""
        self._key_lock = value

    @property
    def key_lock_plus(self) -> bool:
        """Return key lock plus status."""
        return self._key_lock_plus

    @key_lock_plus.setter
    def key_lock_plus(self, value: bool) -> None:
        self._key_lock_plus = value

    @property
    def display_mirrored(self) -> bool:
        return self._display_mirrored

    @display_mirrored.setter
    def display_mirrored(self, value: bool) -> None:
        self._display_mirrored = value

    @property
    def dst(self) -> bool:
        return self._dst

    @dst.setter
    def dst(self, value: bool) -> None:
        self._dst = value

    def _update_hex_string(self):
        pass


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

        self._mqtt_client = Client()
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

    def _publish_connection_test(self):
        self._mqtt_client.publish(
            self._topics.command_topics["CONNECTION_TEST"], const.CONNECTION_TEST_COMMAND
        )
        self._last_connection_test_published = time.time()

    async def connect(self):
        self._mqtt_client.connect(self._mqtt_host, self._mqtt_port)
        self._mqtt_client.loop_start()
        await self.update_standard_values()

    async def disconnect(self):
        self._mqtt_client.disconnect()
        self._mqtt_client.loop_stop()
        self._connected = False

    async def update_values(self, request_value: int = 0xFFFFFFFF) -> None:
        """Update all parameters.

        Use this function to fetch setpoint temperature, ambient temperature, battery level,
        configuration parameters, open window settings etc. Supply the constants in the form REQUEST_TEMPERATURE_SETPOINT | REQUEST_TEMPERATURE_AMBIENT | REQUEST_WIFI_SIGNAL_STRENGTH

        :return: Nothing
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
