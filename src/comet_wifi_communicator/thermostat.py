from dataclasses import dataclass

from paho.mqtt.client import Client, CONNACK_ACCEPTED

from .lib import constants, commands
from .lib.commands import REQUEST_ALL_PARAMS, REQUEST_WIFI_SIGNAL
from .lib.constants import TEMPERATURE_HEX_OFF, TEMPERATURE_SETPOINT_MIN, TEMPERATURE_HEX_ON, TEMPERATURE_SETPOINT_MAX, \
    HEX_PREFIX
from .lib.mqtt_topics import MqttTopics
from .lib.helper import convert_temperature_to_float, convert_hex_to_int, convert_temperature_to_hex
from .lib.helper import validate_and_streamline_mac

@dataclass
class ThermostatConfig:
    _key_lock: bool = False
    _key_lock_plus: bool = False
    _display_mirrored: bool = False
    _dst: bool = False

    _hex_string : str = "#0000"

    @property
    def key_lock(self) -> bool:
        return self._key_lock

    @key_lock.setter
    def key_lock(self, value: bool) -> None:
        self._key_lock = value

    @property
    def key_lock_plus(self) -> bool:
        return self._key_lock_plus

    @key_lock_plus.setter
    def key_lock_plus(self, value: bool) -> None:
        self._key_lock_plus = value

    def _update_hex_string(self):
        pass

class Thermostat:
    def __init__(self, mqtt_host: str, mqtt_port: int, mac: str):
        self._mac = validate_and_streamline_mac(mac)
        self._mqtt_host = mqtt_host
        self._mqtt_port = mqtt_port
        self._connected = False
        self._topics = MqttTopics(self._mac)
        self._values = {
            "temperature_setpoint": 0.0,
            "temperature_ambient": 0.0,
            "temperature_offset": 0.0,
            "window_open": False,
            "is_heating": False,
            "battery_level": 0
        }

        self._mqtt_client = Client()
        self._mqtt_client.on_connect = self._on_mqtt_connect
        self._mqtt_client.on_message = self._on_mqtt_message

        self._mqtt_client.user_data_set([])  # Clear user data from the client

        self._skip_connection_test = False

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def controller_name(self) -> str:
        return self._mqtt_host

    @property
    def setpoint(self) -> float:
        return self._values["temperature_setpoint"]

    @property
    def mac(self) -> str:
        return self._mac

    def _on_mqtt_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code is not CONNACK_ACCEPTED.value:
            raise MQTTConnectError
        # Subscribe from on_connect to be sure that subscription is persisted across reconnections
        for topic in self._topics.reply_topics.values():
            client.subscribe(topic)
        client.subscribe(self._topics.request_topics["CONNECTION_TEST"])

    def _on_mqtt_message(self, client, userdata, message):

        # Thermostat disconnected
        if message.topic == self._topics.reply_topics["WILL"]:
            self._connected = False
            return

        self._connected = True
        if message.topic == self._topics.request_topics["CONNECTION_TEST"] and not self._skip_connection_test:
            self._publish_connection_test()
            return
        else:
            self._skip_connection_test = False

        if message.topic == self._topics.reply_topics["TEMPERATURE_AMBIENT"]:
            self._values["temperature_ambient"] = convert_temperature_to_float(message.payload.decode("utf-8"))
            return

        if message.topic == self._topics.reply_topics["TEMPERATURE_SETPOINT"]:
            payload = message.payload.decode("utf-8")
            if payload == f"{HEX_PREFIX}{TEMPERATURE_HEX_OFF:02X}":
                self._values["is_heating"] = False
                self._values["temperature_setpoint"] = TEMPERATURE_SETPOINT_MIN
                return
            if payload == f"{HEX_PREFIX}{TEMPERATURE_HEX_ON:02X}":
                self._values["temperature_setpoint"] = TEMPERATURE_SETPOINT_MAX
            else:
                self._values["temperature_setpoint"] = convert_temperature_to_float(payload)
            return

        if message.topic == self._topics.reply_topics["BATTERY"]:
            self._values["battery_level"] = convert_hex_to_int(message.payload.decode("utf-8"))
            return

    def _publish_connection_test(self):
        self._mqtt_client.publish(self._topics.request_topics["CONNECTION_TEST"], commands.CONNECTION_TEST)
        self._skip_connection_test = True

    async def connect(self):
        self._mqtt_client.connect(self._mqtt_host, self._mqtt_port)
        self._mqtt_client.loop_start()
        #self._mqtt_client.publish(self._topics.request_topics["GENERAL_VALUE_REQUEST"], "#02000000") # Request temperature for testing
        await self.update_all_values()
        # TODO: Check returned values after some time has passed and set connection state based on that and/or raise error

    async def disconnect(self):
        self._mqtt_client.disconnect()
        self._mqtt_client.loop_stop()
        self._connected = False

    async def update_values(self) -> None:
        # Request ambient temperature
        self._mqtt_client.publish(self._topics.request_topics["GENERAL_VALUE_REQUEST"], "#02000000")
        # Request setpoint and battery
        self._mqtt_client.publish(self._topics.request_topics["GENERAL_VALUE_REQUEST"], "#41000000")

    async def update_all_values(self) -> None:
        """
            Update all available parameters.

            Use this function to fetch setpoint temperature, ambient temperature, battery level,
            configuration parameters, open window settings etc.

            :return: Nothing
            :rtype: None
            Returns
        """
        self._mqtt_client.publish(self._topics.request_topics["GENERAL_VALUE_REQUEST"], REQUEST_ALL_PARAMS)
        self._mqtt_client.publish(self._topics.request_topics["GENERAL_VALUE_REQUEST"], REQUEST_WIFI_SIGNAL)

    async def set_temperature(self, temperature: float) -> None:
        if not self._connected:
            raise
        if temperature > constants.TEMPERATURE_SETPOINT_MAX:
            temperature = constants.TEMPERATURE_SETPOINT_MAX
        if temperature < constants.TEMPERATURE_SETPOINT_MIN:
            temperature = constants.TEMPERATURE_SETPOINT_MIN
        temperature_encoded = convert_temperature_to_hex(temperature)
        self._mqtt_client.publish(self._topics.request_topics["TEMPERATURE_SETPOINT"], temperature_encoded)
        self._values["is_heating"] = True
        self._values["temperature_setpoint"] = temperature

    async def turn_off(self) -> None:
        self._mqtt_client.publish(self._topics.request_topics["TEMPERATURE_SETPOINT"], f"{HEX_PREFIX}{TEMPERATURE_HEX_OFF:02X}")
        self._values["is_heating"] = False

    async def turn_fully_on(self) -> None:
        self._mqtt_client.publish(self._topics.request_topics["TEMPERATURE_SETPOINT"], f"{HEX_PREFIX}{TEMPERATURE_HEX_ON:02X}")
        self._values["is_heating"] = True


class MQTTConnectError(Exception):
    pass

class ThermostatNotConnectedError(Exception):
    pass