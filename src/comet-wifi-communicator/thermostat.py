import logging
from dataclasses import dataclass

from paho.mqtt.client import Client, CONNACK_ACCEPTED

from lib import constants, commands
from lib.mqtt_topics import MqttTopics

_LOGGER = logging.getLogger(__name__)

class Thermostat:
    """Thermostat"""

    id: str
    name: str
    is_heating: bool
    temperature_setpoint: float
    temperature_ambient: float
    temperature_offset: float
    window_open: bool
    battery_level: int


class CometWifiThermostatAPI:
    def __init__(self, mqtt_host: str, mqtt_port: int, mac: str, name: str):
        self._mac = mac
        self._name = name
        self._mqtt_host = mqtt_host
        self._mqtt_port = mqtt_port
        self.connected = False
        self._topics = MqttTopics(mac)

        self._mqtt_client = Client()
        self._mqtt_client.on_connect = self.on_mqtt_connect
        self._mqtt_client.on_message = self.on_mqtt_message

        self._mqtt_client.user_data_set([])  # Clear user data from the client

    @property
    def controller_name(self) -> str:
        return self._mqtt_host

    def on_mqtt_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code is not CONNACK_ACCEPTED:
            raise MQTTConnectError
        # Subscribe from on_connect to be sure that subscription is persisted across reconnections
        for topic in self._topics.reply_topics.values():
            client.subscribe(topic)

    def on_mqtt_message(self, client, userdata, message):
        if message.topic == self._topics.request_topics["CONNECTION_TEST"]:
            self.publish_connection_test()
            return
        if message.topic == self._topics.reply_topics["TEMPERATURE_AMBIENT"]:
            self.device.temperature_ambient = convert_temperature_to_float(message.payload.decode("utf-8"))
            return
        if message.topic == self._topics.reply_topics["TEMPERATURE_SETPOINT"]:
            payload = message.payload.decode("utf-8")
            if payload == constants.TEMPERATURE_HEX_OFF:
                self.device.is_heating = False
                self.device.temperature_setpoint = 8
                return
            self.device.is_heating = True
            self.device.temperature_setpoint = convert_temperature_to_float(message.payload.decode("utf-8"))
            return
        if message.topic == self._topics.reply_topics["BATTERY"]:
            self.device.battery_level = convert_hex_to_int(message.payload.decode("utf-8"))
            return

    def publish_connection_test(self):
        self._mqtt_client.publish(self._topics.request_topics["CONNECTION_TEST"], commands.CONNECTION_TEST)

    async def connect(self):
        self._mqtt_client.connect(self._mqtt_host, self._mqtt_port)
        self._mqtt_client.loop_start()
        self.connected = True
        self._mqtt_client.publish(self._topics.request_topics["GENERAL_VALUE_REQUEST"], "#02000000") # Request temperature for testing

    async def disconnect(self):
        self._mqtt_client.disconnect()
        self._mqtt_client.loop_stop()
        self.connected = False

    async def update_values(self) -> None:
        # Request ambient temperature
        self._mqtt_client.publish(self._topics.request_topics["GENERAL_VALUE_REQUEST"], "#02000000")
        # Request setpoint and battery
        self._mqtt_client.publish(self._topics.request_topics["GENERAL_VALUE_REQUEST"], "#41000000")

    async def set_thermostat_temperature(self, temperature: float) -> None:
        temperature_encoded = convert_temperature_to_hex(temperature)
        self._mqtt_client.publish(self._topics.request_topics["TEMPERATURE_SETPOINT"], temperature_encoded)
        self.device.is_heating = True
        self.device.temperature_setpoint = temperature

    async def turn_off_thermostat(self) -> None:
        self._mqtt_client.publish(self._topics.request_topics["TEMPERATURE_SETPOINT"], constants.TEMPERATURE_HEX_OFF)
        self.device.is_heating = False

    async def turn_fully_on(self) -> None:
        self._mqtt_client.publish(self._topics.request_topics["TEMPERATURE_SETPOINT"], constants.TEMPERATURE_HEX_ON)
        self.device.is_heating = True


class MQTTConnectError(Exception):
    pass
