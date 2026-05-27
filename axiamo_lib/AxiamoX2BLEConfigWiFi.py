import asyncio
from AxiamoX2BLEOfflineRecorder import AxiamoX2BLEOfflineRecorder
import json


async def configWifiAndReboot(x2Dldr : AxiamoX2BLEOfflineRecorder):
    await x2Dldr.scan()
    for bleMac in x2Dldr.x2Ble.scanned_devices:
        print(f"Found X2 device: {bleMac}")

    config_data={}
    with open("configuration.json", 'r') as file:
        config_data = json.load(file)

    bleMac = config_data.get("bleMac")
    ssid = config_data.get("ssid")
    wifipwd = config_data.get("wifipwd")
    

    
    print(f"Connecting to: {bleMac}")
    await x2Dldr.connect(bleMac)
    await x2Dldr.configWifi(ssid,wifipwd)
    await x2Dldr.setup()
    await x2Dldr.saveSettings()
    await x2Dldr.reboot()
    await asyncio.sleep(0.5)
    await x2Dldr.disconnect()

if __name__ == "__main__":
    x2Dldr = AxiamoX2BLEOfflineRecorder()
    asyncio.run(configWifiAndReboot(x2Dldr))
   