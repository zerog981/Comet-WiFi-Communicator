GROUP_COMMAND = "S"
GROUP_REPLY = "V"
GROUP_TIME = "T"
SEPARATOR = "/"

class MqttTopics:

    def __init__(self, mac, mode_prefix="01"):

        topic_structure = mode_prefix + SEPARATOR + mac + SEPARATOR

        # Request topics
        command_topic_structure = topic_structure + GROUP_COMMAND + SEPARATOR

        self.command_topics = {
            "GENERAL_VALUE_REQUEST":      command_topic_structure + "AF",
            "CONNECTION_TEST":            command_topic_structure + "XX",
            "WRITE_TEMPERATURE_SETPOINT":       command_topic_structure + "A0",
            #"TEMPERATURE_OFFSET":         command_topic_structure + "A2",
            #"CONFIGURATION":              command_topic_structure + "A3",
            #"WINDOW_OPEN_CONFIGURATION":  command_topic_structure + "A5",
            #"BATTERY":                    command_topic_structure + "A6",
            #"BASE_SOFTWARE":              command_topic_structure + "B1",
            #"WIFI_SOFTWARE":              command_topic_structure + "B2",
            #"WIFI_SIGNAL":                command_topic_structure + "B3"
        }

        reply_topic_structure = topic_structure + GROUP_REPLY + SEPARATOR
        self.reply_topics = {
            "TEMPERATURE_SETPOINT": reply_topic_structure + "A0",
            "TEMPERATURE_AMBIENT":  reply_topic_structure + "A1",
            "TEMPERATURE_OFFSET":   reply_topic_structure + "A2",
            "CONFIGURATION":        reply_topic_structure + "A3",
            "KEY_LOCK_PLUS_STATE":  reply_topic_structure + "BD",
            "BATTERY":              reply_topic_structure + "A6",
            "WILL":                 reply_topic_structure + "XX",
        }

