import logging
from paho.mqtt.client import Client, CONNACK_ACCEPTED

from lib import constants, commands
from lib.mqtt_topics import MqttTopics
from lib.helper import convert_temperature_to_float, convert_hex_to_int, convert_temperature_to_hex

_LOGGER = logging.getLogger(__name__)

class Thermostat:
    def __init__(self, mqtt_host: str, mqtt_port: int, mac: str, name: str):
        self._mac = mac
        self._name = name
        self._mqtt_host = mqtt_host
        self._mqtt_port = mqtt_port
        self.connected = False
        self._topics = MqttTopics(mac)
        self._values = {
            "temperature_setpoint": 0.0,
            "temperature_ambient": 0.0,
            "temperature_offset": 0.0,
            "window_open": False,
            "is_heating": False,
            "battery_level": 0
        }

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
            self._values["temperature_ambient"] = convert_temperature_to_float(message.payload.decode("utf-8"))
            return
        if message.topic == self._topics.reply_topics["TEMPERATURE_SETPOINT"]:
            payload = message.payload.decode("utf-8")
            if payload == convert_temperature_to_hex(constants.TEMPERATURE_OFF):
                self._values["is_heating"] = False
                self._values["temperature_setpoint"] = constants.TEMPERATURE_OFF
                return
            self._values["is_heating"] = True
            self._values["temperature_setpoint"] = convert_temperature_to_float(message.payload.decode("utf-8"))
            return
        if message.topic == self._topics.reply_topics["BATTERY"]:
            self._values["battery_level"] = convert_hex_to_int(message.payload.decode("utf-8"))
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
        self._values["is_heating"] = True
        self._values["temperature_setpoint"] = temperature

    async def turn_off_thermostat(self) -> None:
        self._mqtt_client.publish(self._topics.request_topics["TEMPERATURE_SETPOINT"], constants.TEMPERATURE_HEX_OFF)
        self._values["is_heating"] = False

    async def turn_fully_on(self) -> None:
        self._mqtt_client.publish(self._topics.request_topics["TEMPERATURE_SETPOINT"], constants.TEMPERATURE_HEX_ON)
        self._values["is_heating"] = True


class MQTTConnectError(Exception):
    pass
