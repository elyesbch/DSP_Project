from enum import Enum


class BLEState(Enum):
    startup = 0
    idle = 1
    scanning = 2
    scan_complete = 3
    connecting = 4
    connected = 5
    receiving = 6
    disconnecting = 7


class Commands:
    scan = "SCAN"
    connect = "CONNECT"
    subscribe = "SUBSCRIBE"
    unsubscribe = "UNSUBSCRIBE"
    add_charac_needle = "ADDCHARACTERISTIC"
    remove_charac_needle = "RMCHARACTERISTIC"
    disconnect = "DISCONNECT"
    set_record = "RECORD"
    set_record_meta = "METADATA"
    set_offline_meta = "METADATAOFFLINE"
    set_tag = "SETTAG"
    # stop_record = "STOPRECORD"
    # stop = "STOP"
    set_user = "SET_USER"
    set_activity = "SET_ACTIVITY"
    set_devname = "SET_DEV_NAME"
    powermeter_calibrate = "POWER_METER_CALIBRATE"
    download_offline_recordings = "DOWNLOAD_OFFLINE_RECORDINGS"
    get_full_state = "GET_FULL_STATE"
    kill = "KILL"
    # openFiles = "OPEN_FILES"
    # stopRecording = "STOP_RECORD"


validServiceUUIds = [
    "1810",
    "181F",
    "1818",
    "1816",
    "1826",
    "1808",
    "1809",
    "180D",
    "181D",
    "183E",
]

desiredCharacteristicUuids = [
    "2A63",
    "2A9A",
    "2A5B",
    "2A37",
]

axiamoX2UserIdxUuid = "00002a9a-0000-1000-8000-00805f9b34fb"

userIdxUuidNeedle = "2A9A"
ftpUuidNeedle = "FFFB"
cyclingPowerMeasurementUuid = "00002a63-0000-1000-8000-00805f9b34fb"
batteryLevelUuid = "00002a19-0000-1000-8000-00805f9b34fb"


x22CmdHeader = 0x7C
DATA_TYPE_FILEINFO = 0x90
DATA_TYPE_FILEPART = 0x91

x22ImuPeripheralIndex = 3
x22SetModePayloadCmd = 1 << 3
imuConfigGyr4000DPS = 0x00060000
imuConfigRaw200Hz = 0x00000004
imuConfigAcc16GFsr = 0x00000400
MAG_FSR_4GAUSS          = 0x00100000
MAG_FSR_8GAUSS          = 0x00200000
MAG_FSR_12GAUSS         = 0x00300000
MAG_FSR_16GAUSS         = 0x00400000

imuConfigGyrXPrimaryAxisOnly = 0x00100000
imuConfigGyrYPrimaryAxisOnly = 0x00200000
imuConfigGyrZPrimaryAxisOnly = 0x00300000

x22ParamHeader = 0x7D
x22ParamCtxSetDatetime = 8
x22ParamCtxSetOfflineRecording = 9

x22RequestHeader = 0x7E
