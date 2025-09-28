from collections import namedtuple

STARTUP = r"""
  ______                 _____ ____  
 |  ____|               |_   _/ __ \ 
 | |__   __ _ ___ _   _    | || |  | |
 |  __| / _` / __| | | |   | || |  | |
 | |___| (_| \__ \ |_| |  _| || |__| |
 |______\__,_|___/\__, | |_____\___\_|
                   __/ |              
                  |___/               
EasyIQ integration, version: %s
This is a custom integration for EasyIQ
Based on the Aula component with fixes for EasyIQ integration issues
If you have any issues with this you need to open an issue here:
https://github.com/easyiq/easyiq-ha/issues
-------------------------------------------------------------------
"""

DOMAIN = "aula_easyiq"

# API Endpoints
API = "https://www.aula.dk/api/v"
API_VERSION = "22"
EASYIQ_API = "https://api.easyiqcloud.dk/api/aula"

# Widget IDs for EasyIQ
EASYIQ_WEEKPLAN_WIDGET_ID = "0128"  # EasyIQ Weekplan
EASYIQ_HOMEWORK_WIDGET_ID = "0142"  # EasyIQ Homework

# Widget ID mapping
EASYIQ_WIDGETS = {
    "weekplan": EASYIQ_WEEKPLAN_WIDGET_ID,
    "homework": EASYIQ_HOMEWORK_WIDGET_ID,
}

# Configuration keys
CONF_SCHOOLSCHEDULE = "schoolschedule"
CONF_WEEKPLAN = "weekplan"
CONF_HOMEWORK = "homework"
CONF_PRESENCE = "presence"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

# Update interval configuration keys
CONF_WEEKPLAN_INTERVAL = "weekplan_interval"
CONF_HOMEWORK_INTERVAL = "homework_interval"
CONF_PRESENCE_INTERVAL = "presence_interval"
CONF_MESSAGES_INTERVAL = "messages_interval"

# Days forward configuration keys
CONF_WEEKPLAN_DAYS = "weekplan_days"
CONF_HOMEWORK_DAYS = "homework_days"

# Default configuration
DEFAULT_NAME = "EasyIQ"
DEFAULT_WEEKPLAN_INTERVAL = 900  # 15 minutes
DEFAULT_HOMEWORK_INTERVAL = 900  # 15 minutes
DEFAULT_PRESENCE_INTERVAL = 300  # 5 minutes
DEFAULT_MESSAGES_INTERVAL = 300  # 5 minutes
DEFAULT_WEEKPLAN_DAYS = 5  # 5 business days
DEFAULT_HOMEWORK_DAYS = 5  # 5 business days

# Presence status codes
PRESENCE_STATUS = {
    0: "IKKE KOMMET",      # Not arrived
    1: "SYG",              # Sick
    2: "FERIE/FRI",        # Holiday/Free
    3: "KOMMET/TIL STEDE", # Arrived/Present
    4: "PÅ TUR",           # On trip
    5: "SOVER",            # Sleeping
    8: "HENTET/GÅET",      # Picked up/Gone
}

# Error codes
ERROR_UNKNOWN = "unknown_error"
ERROR_AUTH_FAILED = "auth_failed"
ERROR_CONNECTION = "connection_error"
ERROR_TIMEOUT = "timeout_error"