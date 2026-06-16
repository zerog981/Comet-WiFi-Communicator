import socket
import time
from logging import Logger

from comet_wifi_communicator.helper import (
    ip_to_hex_str,
    string_to_unicode,
    int_to_hex_str,
)


def send_config_data(  # nosec B107
    wifi_ssid: str,
    wifi_password: str,
    mqtt_server_ip: str = "0.0.0.0",  # nosec B104
    mqtt_user: str = "00000000",
    mqtt_password: str = "0000000000000000",
    mqtt_port: int = 1883,
    comet_wifi_ip: str = "10.0.0.1",
    comet_wifi_port: int = 1233,
    logger: Logger = None,
) -> bool:
    """Send configuration data to a Comet WiFi thermostat.

    This function prepares and transmits configuration data for WiFi and MQTT connection settings to a Comet WiFi
    thermostat.

    :param wifi_ssid: The WiFi network name (SSID) to configure the thermostat should use.
    :param wifi_password: The password for the WiFi network the thermostat should use.
    :param mqtt_server_ip: The MQTT server IP address. If "0.0.0.0" is used, the device will try to connect to mqtt.eurotronic.io, mqtt2.eurotronic.io, or mqtt3.eurotronic.io. nosec B104
    :param mqtt_user: MQTT server username in hex. Defaults to "00000000". Only effective if MQTT
        server IP is "0.0.0.0". Must be hex formatted.
    :param mqtt_password: MQTT server password in hex. Defaults to "0000000000000000". Only effective
        if MQTT server IP is "0.0.0.0". Must be hex formatted.
    :param mqtt_port: MQTT server port. Defaults to 1883.
    :param comet_wifi_ip: IP address of the Comet WiFi device (hotspot). Defaults to "10.0.0.1".
    :param comet_wifi_port: Port of the Comet WiFi device (hotspot). Defaults to 1233.
    :param logger: Logger for progress and errors

    :return: True on success, False on error.

    :raises socket.error: If there are issues establishing or sending data through the socket connection.
    """

    if logger:
        logger.info(
            f"SSID: {wifi_ssid}, MQTT Broker: {mqtt_server_ip}:{mqtt_port}, Comet Endpoint: {comet_wifi_ip}:{comet_wifi_port}"
        )

    mqtt_server_hex = ip_to_hex_str(mqtt_server_ip, uppercase=True)
    separator = ","

    wifi_ssid_hex = string_to_unicode(wifi_ssid, uppercase=True)
    wifi_password_hex = string_to_unicode(wifi_password, uppercase=True)
    mqtt_port_hex = int_to_hex_str(mqtt_port, uppercase=True)
    mqtt_port_hex = mqtt_port_hex.zfill(4)

    # Note: separator really only for WiFi info in hex
    data = (
        wifi_ssid_hex
        + string_to_unicode(separator, uppercase=True)
        + wifi_password_hex
        + separator
        + mqtt_user
        + separator
        + mqtt_password
        + separator
        + mqtt_server_hex
        + separator
        + mqtt_port_hex
    )

    if logger:
        logger.info("Configuring connection.")
    success = False
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)  # Necessary for Linux Wayland?
    try:
        server = (comet_wifi_ip, comet_wifi_port)
        s.connect(server)
        if logger:
            logger.info("Successfully connected to thermostat.")
        try:
            if logger:
                logger.info("Sending data.")
            s.sendall(bytes(data, "utf-8"))
            time.sleep(2)  # Necessary for Linux Wayland?
            if logger:
                logger.info("Data successfully transmitted.")
            success = True
        except socket.timeout:
            if logger:
                logger.error("Error sending data.")
    except socket.timeout:
        if logger:
            logger.error("Unable to connect to thermostat")

    finally:
        s.close()

    return success
