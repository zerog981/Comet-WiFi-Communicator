"""CLI tools"""
from argparse import ArgumentParser

from comet_wifi_communicator.setup_thermostat import send_config_data

def setup_thermostat() -> None:
    """CLI command for setting up thermostat.

    """
    parser = ArgumentParser()
    parser.add_argument(
        "--wifi-ssid",
        action="store",
        type=str,
        required=True,
        help="WiFi SSID the thermostat should be connected to.",
    )
    parser.add_argument(
        "--wifi-password",
        action="store",
        type=str,
        required=True,
        help="WiFi password for the WiFi network the thermostat should be connected to.",
    )
    parser.add_argument(
        "--mqtt-server-ip",
        action="store",
        type=str,
        required=True,
        help="MQTT server IP address."
    )
    parser.add_argument(
        "--mqtt-server-port",
        action="store",
        type=int,
        default=1883,
        help="MQTT server port.",
    )

    args = parser.parse_args()

    send_config_data(
        wifi_ssid=args.wifi_ssid,
        wifi_password=args.wifi_password,
        mqtt_server_ip=args.mqtt_server_ip,
        mqtt_port=args.mqtt_server_port,
    )

if __name__ == "__main__": # pragma: no cover
    setup_thermostat()