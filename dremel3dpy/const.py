"""Constants for the Dremel 3D Printer (3D20, 3D40, 3D45) integration."""

SERVICE_PRINT_JOB = "print_job"
SERVICE_PAUSE_JOB = "pause_job"
SERVICE_RESUME_JOB = "resume_job"
SERVICE_STOP_JOB = "stop_job"
ATTR_FILEPATH = "file_path"
ATTR_URL = "url"
ATTR_DEVICE_ID = "device_id"

COMMAND_PORT = 80
CAMERA_PORT = 10123
EXTRA_STATUS_PORT = 11134

COMMAND_PATH = "/command"
HOME_MESSAGE_PATH = "/getHomeMessage"
PRINT_FILE_UPLOADS = "/print_file_uploads"

PRINTER_STATUS_COMMAND = "GETPRINTERSTATUS"
PRINTER_INFO_COMMAND = "GETPRINTERINFO"
PRINT_COMMAND = "PRINT"
RESUME_COMMAND = "RESUME"
PAUSE_COMMAND = "PAUSE"
CANCEL_COMMAND = "CANCEL"

STATS_FILE_NAME = "file_name"
STATS_FILAMENT_USED = "filament_used"
STATS_LAYER_HEIGHT = "layer_height"
STATS_SOFTWARE = "software"
STATS_INFILL_SPARSE_DENSITY = "infill_sparse_density"

EVENT_DATA_NEW_PRINT_STATS = "dremel_3d_printer_new_print_stats"

REQUEST_TIMEOUT = 30

MESSAGE = "message"
ERROR_CODE = "error_code"

CONF_TITLE = "title"
CONF_MODEL = "model"
CONF_SERIAL_NUMBER = "SN"
CONF_API_VERSION = "api_version"
CONF_FIRMWARE_VERSION = "firmware_version"
CONF_MACHINE_TYPE = "machine_type"
CONF_WIFI_IP = "wifi_ip"
CONF_WIFI_CONNECTED = "wifi_connected"
CONF_ETHERNET_IP = "ethernet_ip"
CONF_ETHERNET_CONNECTED = "ethernet_connected"
CONF_CONNECTION_TYPE = "connection_type"

ELAPSED_TIME = ["elaspedtime", "elapsed_time"]
ESTIMATED_TOTAL_TIME = ["totalTime", "estimated_total_time"]
REMAINING_TIME = ["remaining", "remaining_time"]
PROGRESS = ["progress", "progress"]
STATUS = ["status", "current_status"]
DOOR_OPEN = ["door_open", "door_open"]
FILAMENT = ["filament_type ", "filament"]
FAN_SPEED = ["fanSpeed", "fan_speed"]
CHAMBER_TEMPERATURE = ["chamber_temperature", "chamber_temperature"]
PLATFORM_TEMPERATURE = ["platform_temperature", "platform_temperature"]
PLATFORM_TARGET_TEMPERATURE = [
    "buildPlate_target_temperature",
    "platform_target_temperature",
]
EXTRUDER_TEMPERATURE = ["temperature", "extruder_temperature"]
EXTRUDER_TARGET_TEMPERATURE = [
    "extruder_target_temperature",
    "extruder_target_temperature",
]
JOB_STATUS = [
    "jobstatus",
    "job_status",
]
JOB_NAME = ["jobname", "job_name"]
NETWORK_BUILD = ["networkBuild", "network_build"]

USAGE_COUNTER = ["UsageCounter", "hours_used"]
AVAILABLE_STORAGE = ["PrintererAvailabelStorage", "available_storage"]
PLATFORM_TEMPERATURE_RANGE = ["PrinterBedMessage", "platform_max_temperature"]
EXTRUDER_TEMPERATURE_RANGE = ["PrinterNozzleMessage", "extruder_max_temperature"]
