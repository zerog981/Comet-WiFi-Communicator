# Comet-WiFi-Communicator
[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/Y8Y11TZWBX)

A library for setting up of and asynchronous communication with Comet WiFi Thermostats over a custom MQTT broker. This library is also the backend to the corresponding Home Assistant integration.

## 🚀 Introduction
Comet WiFi Thermostats usually communicate with the Eurotronic MQTT brokers and require a dedicated app. This library allows changing the configuration of Comet WiFi thermostats to use a custom MQTT broker instead. With this setup it is possible to control your thermostats from within your LAN without any Internet connection.

⚠️ Using this library is not compatible with the stock Eurotronic Smart Living app. If you want to change the configuration back to the stock configuration, reset the thermostat and follow the official setup guide. 

️⚠️ This library uses undocumented functionality of the thermostat firmware with a very small risk to brick your thermostat. You perform all actions below on your own risk.

## ✅ Requirements
- Comet WiFi Thermostat
- MQTT Broker without authenitication
- Python 3.14

## 🛠️ Installation and Setup

⚠️ Resetting your thermostat will delete all data stored on the thermostat (schedules, etc.).
1. Install library: `pip install commet-wifi-communicator`
2. Make sure your MQTT broker is setup and running.
2. Reset Thermostat (follow official instructions)
   1. Use a pin to press and hold the reset button in the battery tray until the display is off.
   2. Release the button.
   3. Remove the batteries and re-insert the batteries.
   4. After a few seconds, the display should show "PA" (pairing) and the Wi-Fi symbol should blink.
2. Connect your PC to the thermostat Wi-Fi. SSID:`Comet Wifi`, Password `11223344`.
3. In a terminal, run `setup_thermostat --wifi-ssid YOUR_SSID --wifi-password YOUR_PASSWORD --mqtt-broker YOUR_MQTT_BROKER_IP`. Optionally you can also specify the MQTT port with the `--mqtt-port` flag.

## 🌡️ Communicate with Thermostat
### Connect and set temperature
```python
import time
from asyncio import run

from comet_wifi_communicator.thermostat import Thermostat

thermostat = Thermostat(mqtt_host="192.168.0.10", mqtt_port=1883, mac="AA:BB:CC:DD:EE:FF")
run(thermostat.connect())

# Queries thermostat for setpoint temperature, ambient temperature, and temperature offset
run(thermostat.update_heating_values())
time.sleep(3) # Wait for thermostat to respond

# Get ambient temperature and setpoint
print(thermostat.setpoint)
print(thermostat.temperature_ambient)

# Change setpoint to 27.5°C
run(thermostat.set_temperature(27.5))
time.sleep(3) # Wait for thermostat to respond
print(thermostat.setpoint)
```
For more information about the library, have a look at the [thermostat.py](src/comet_wifi_communicator/thermostat.py) file.

## 🚧 Limitations
- Thermostat does not support SSL
- Thermostat does not support MQTT authentication when using custom MQTT broker 
- The thermostat will regularly send ping messages to MQTT. While running, the Thermostat library will automatically handle these requests. Therefore, it has to be kept running.

## 📜 License
GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007, see the [license file](LICENSE).