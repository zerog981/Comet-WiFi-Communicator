# Comet-WiFi-Communicator
[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/Y8Y11TZWBX)

A library for setting up of and communication with Comet WiFi Thermostats over a custom MQTT broker.

## Introduction
Comet WiFi thermostats usually communicate with the Eurotronic MQTT brokers and require a dedicated app. This library allows changing the configuration of Comet WiFi thermostats to use a custom MQTT broker instead. With this setup it is possible to control your thermostats from within your LAN without any Internet connection.

⚠️ Using this library is not compatible with the stock Eurotronic Smart Living app. If you want to change the configuration back to the stock configuration, reset the thermostat and follow the official setup guide. 

## Requirements
- Comet WiFi Thermostat
- MQTT Broker without authenitication
- Python 3.14

## Installation
`pip install commet-wifi-communicator`

## Thermostat Setup
⚠️ This library uses undocumented functionality of the thermostat firmware with a very small risk to brick your thermostat. You perform all actions below on your own risk.
1. Reset Thermostat
2. 
