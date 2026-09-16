# Comet-WiFi-Communicator

Command-line tool that points Eurotronic Comet WiFi radiator thermostats at **your own MQTT
broker**, so they work inside your LAN without the manufacturer's cloud or app.

Out of the box a Comet WiFi thermostat only talks to the Eurotronic cloud. After a factory reset it opens
a Wi-Fi hotspot. This tool allows for configuring the thermostat then in a way that it talks to your own
broker. Once this is done, thermostats can be controlled with [`aiocometwifi`](https://pypi.org/project/aiocometwifi/) 
or the Home Assistant integration built on top of it.

⚠️ A thermostat configured this way no longer works with the Eurotronic Smart Living app. To go
back, reset it and follow the official setup guide.

⚠️ This tool uses undocumented firmware functionality to customize the broker. There is a small risk of
bricking your thermostat. Everything below is at your own risk.

- One command: `comet-wifi-communicator setup`.
- Zero runtime dependencies, fully typed, Python ≥ 3.12.

## ✅ Prerequisites

1. **An MQTT broker on your LAN that accepts anonymous clients.** The thermostats cannot be
   given credentials. See [Broker](#-broker).
2. **Python ≥ 3.12**, or [pipx](https://pipx.pypa.io/) / [uv](https://docs.astral.sh/uv/), 
   on a computer with Wi-Fi (it has to join the thermostat's hotspot).

## 📦 Installation

Run it without installing anything permanently (pipx and uv fetch it into a temporary
environment):

```bash
pipx run comet-wifi-communicator setup --help
uvx comet-wifi-communicator setup --help
```

Or install it as a command:

```bash
pipx install comet-wifi-communicator   # or: uv tool install comet-wifi-communicator
pip install comet-wifi-communicator    # into a virtual environment
```

## 🔧 Setting up a thermostat

Repeat for every thermostat. Have the broker's IPv4 address at hand (a host name will not do,
the thermostat cannot resolve names).

1. **Reset the thermostat.** ⚠️ This erases everything stored on it, schedules included.
   1. With a pin, press and hold the reset button in the battery tray until the display turns off.
   2. Release the button.
   3. Remove the batteries and re-insert them.
   4. After a few seconds the display shows `PA` (pairing) and the Wi-Fi symbol blinks.
2. **Connect your computer to the thermostat's Wi-Fi hotspot.** SSID `Comet Wifi`, password
   `11223344`.
3. **Send the configuration:**

   ```bash
   comet-wifi-communicator setup --wifi-ssid <your ssid> --mqtt-server-ip <broker ip>
   ```

   You are prompted for the Wi-Fi password (leave it empty for an open network). Pass
   `--wifi-password` instead if you want to script it (warning: it stays in your shell history).
4. **Reconnect your computer to your own network.** The thermostat closes the hotspot and joins
   the network you named.

Verify with any MQTT client, for example:

```bash
mosquitto_sub -h <broker ip> -t '01/#' -v
```

The thermostat announces itself on `01/<MAC>/S/XX` (its connection test) when it connects and
then from time to time.

`setup` also prints the thermostat's MAC address, which Home Assistant asks for when you add
the thermostat. This is an experimental function (it is derived from the hotspot's address in your
computer's ARP table). In case the lookup fails or the thermostat cannot be found in Home Assistant,
look the MAC address up in your router instead.

All options:

| Option | Meaning                                                                       |
|---|-------------------------------------------------------------------------------|
| `--wifi-ssid` | Wi-Fi network the thermostat should join (required).                          |
| `--wifi-password` | Wi-Fi network password, prompted for when omitted. Empty for an open network. |
| `--mqtt-server-ip` | IPv4 address of the broker (required).                                        |
| `--mqtt-server-port` | Broker port, default `1883`.                                                  |
| `--thermostat-ip`, `--thermostat-port` | Where the thermostat listens inside its hotspot, default `10.0.0.1:1233`.     |
| `-v`, `--verbose` | Debug output and full error details.                                          |

Limits set by the firmware:
- SSID and password must be printable ASCII without a comma
- SSID length limited to 32 characters
- No TLS
- No MQTT authentication
- No IPv6.

## 📡 Broker

The thermostats connect **anonymously**. Run a broker with `allow_anonymous true`, and restrict
what anonymous clients may access with an ACL (the devices only need the `01/#` topic tree).
Keep the broker off the public internet. With Mosquitto:

```conf
# mosquitto.conf
listener 1883
allow_anonymous true
acl_file /mosquitto/config/acl
```

```conf
# acl - entries before the first `user` line apply to anonymous clients
topic readwrite 01/#
```

Note: The official Home Assistant Mosquitto add-on refuses anonymous clients by design. However, the integration's documentation describes how to bridge a small anonymous broker into it.

## ↩️ Back to the stock app

Reset the thermostat as above and follow the official Eurotronic setup guide. Nothing this
tool does is permanent.

## 🔗 Relation to `aiocometwifi`

This package used to bundle an MQTT client for talking to the thermostats. That part now lives
in [`aiocometwifi`](https://pypi.org/project/aiocometwifi/), an async library over a
caller-supplied MQTT transport.

## 🛠️ Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e . -r requirements_dev.txt
pre-commit install
pytest --cov --cov-fail-under=90 --cov-report=term-missing
ruff check . && ruff format --check . && mypy
```


## ⚖️ Disclaimer

This is an independent, community-developed project. It is not affiliated with, endorsed by or
supported by Eurotronic. *Eurotronic* and *Comet WiFi* are trademarks or trade names of their
respective owners and are used here only to identify the devices this tool configures. Use at
your own risk. See the license for the warranty disclaimer.

While I am somewhat skeptical towards blindly allowing AI for coding and do not support the way
major companies are selling and training their models, the usefulness for reviewing and improving
software cannot be denied. Therefore, for enhancing the quality of parts of this tool and finding
issues, AI (mostly Claude Opus 5) was utilized.

## 📜 License

GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007, see the [license file](LICENSE).
