GROUP_REQUEST = "S"
GROUP_REPLY = "V"
GROUP_TIME = "T"
SEPARATOR = "/"

class MqttTopics:

    def __init__(self, mac, mode_prefix="01"):

        topic_structure = mode_prefix + SEPARATOR + mac + SEPARATOR

        # Request topics
        request_topic_structure = topic_structure + GROUP_REQUEST + SEPARATOR

        self.request_topics = {
            "GENERAL_VALUE_REQUEST":      request_topic_structure + "AF",
            "CONNECTION_TEST":            request_topic_structure + "XX",
            "TEMPERATURE_SETPOINT":       request_topic_structure + "A0",
            "TEMPERATURE_OFFSET":         request_topic_structure + "A2",
            "CONFIGURATION":              request_topic_structure + "A3",
            "WINDOW_OPEN_CONFIGURATION":  request_topic_structure + "A5",
            "BATTERY":                    request_topic_structure + "A6",
            "BASE_SOFTWARE":              request_topic_structure + "B1",
            "WIFI_SOFTWARE":              request_topic_structure + "B2",
            "WIFI_SIGNAL":                request_topic_structure + "B3"
        }

        reply_topic_structure = topic_structure + GROUP_REPLY + SEPARATOR
        self.reply_topics = {
            "TEMPERATURE_SETPOINT": reply_topic_structure + "A0",
            "TEMPERATURE_AMBIENT":  reply_topic_structure + "A1",
            "CONFIGURATION":        reply_topic_structure + "A3",
            "KEY_LOCK_PLUS_STATE":  reply_topic_structure + "BD",
            "BATTERY":              reply_topic_structure + "A6",
            "WILL":                 reply_topic_structure + "XX",
        }

