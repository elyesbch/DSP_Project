import asyncio
import datetime
from axiamo_lib.BaseLogger import Logger
import tzlocal
from pathlib import Path
import os
import re
from axiamo_lib.bluetooth_interface.util.dataParser import Parser
from axiamo_lib.AxiamoX2Composer import *


class AxiamoX2Ble:
    x2 = {
        "name": None,
        "client": None,
        "device": None,
        "adv_data": None,
    }
    parser = Parser(logf=Logger.info)
    
    async def scan(self):
        Logger.info("scanning for BLE devices")
        scanned_devices = await bleak.BleakScanner.discover(1, return_adv=True)
        self.scanned_devices = {}
        for deviceName in scanned_devices:
            adv_data = scanned_devices[deviceName][1]

            if adv_data.local_name and adv_data.local_name.find("X22") >= 0:
                Logger.info("Found AxiamoX2 device:")
                Logger.info(f"{adv_data.local_name} {adv_data.rssi}dB")
                self.scanned_devices[deviceName] = scanned_devices[deviceName]
        Logger.info("Scan done")

    async def showDeviceInfos(self):
        for deviceName in self.scanned_devices:
            device = self.scanned_devices[deviceName][0]
            adv_data = self.scanned_devices[deviceName][1]
            Logger.info(f"Device: {device}")
            Logger.info(f"AdvData: {adv_data}")

    async def connectByAddress(self, address):
        try:
            self.x2["client"] = BleakClient(address)
            await self.x2["client"].connect()
            # self.x2["device"] = device
            # self.x2["adv_data"] = adv_data
            # self.x2["name"] = adv_data.local_name

            Logger.info("Axiamo X2 connected.")

        except bleak.exc.BleakError as e:
            Logger.error(f"  error {e}")
            await asyncio.sleep(1)


    async def connect(self, deviceName):
        device_to_connect = None
        for key, value in self.scanned_devices.items():
            adv_data = value[1]
            if adv_data.local_name[-8:] == deviceName[-8:]:
                device_to_connect = value
                break

        if device_to_connect is None:
            Logger.error(f"Device {deviceName} not found in scanned devices.")
            return

        adv_data = device_to_connect[1]
        device = await BleakScanner.find_device_by_name(adv_data.local_name)  #self.scanned_devices[deviceName][0]

        Logger.info(f"Connecting to {adv_data.local_name} ...")
        try:
            self.x2["client"] = BleakClient(
                device, disconnected_callback=self.handle_disconnect
            )
            await self.x2["client"].connect()
            self.x2["device"] = device
            self.x2["adv_data"] = adv_data
            self.x2["name"] = adv_data.local_name

            Logger.info("Axiamo X2 connected.")

        except bleak.exc.BleakError as e:
            Logger.error(f"  error {e}")
            await asyncio.sleep(1)

    async def disconnect(self):
        if self.x2["client"]:
            await self.x2["client"].disconnect()

    def handle_disconnect(self, _: BleakClient):
        self.x2 = {
            "name": None,
            "client": None,
            "device": None, 
            "adv_data": None,
        }
        Logger.info("Device was disconnected, goodbye.")

    async def handle_rx(self, _: int, data: bytearray):
        # self.bytesReceived += len(data)
        self.parser.parseStream(bytes(data))

        # Logger.info(f"Parsed: {self.parser.dataBuffer.maxLen()}")

    async def subscribe(self, client: BleakClient, char_spec, callback):
        await client.start_notify(char_spec, callback)

    async def unsubscribe(self, client: BleakClient, char_spec):
        await client.stop_notify(char_spec)

    async def send_data(self, client, char_spec, data):
        await client.write_gatt_char(char_spec, data, True)
        # Logger.info(f"Answer: {answer}")

    async def send_data_with_response(self, client, char_spec, data):
        await client.start_notify(char_spec, self.handle_rx)
        answer = await client.write_gatt_char(char_spec, data, response=True)

        await asyncio.sleep(
            0.2
        )  # Sleeping just to make sure the response is not missed...
        await client.stop_notify(char_spec)

    def listDevices(self):
        return self.x2s


class AxiamoX2BLEOfflineRecorder:
    DATA_TYPE_FILEINFO = 0x90
    DATA_TYPE_FILEPART = 0x91
    filenameToFetch = ""
    fileSizeToFetch = 0
    downloadedSize = 0
    currentClient = None
    ftpCharacteristic = None
    fetchingFileData = False
    waitingForData = False
    noMoreFiles = False
    fileBuffer = bytearray()
    

    def __init__(self) -> None:
        self.x2Ble = AxiamoX2Ble()
        self.composer = X2composer()
        self.totalBytesThisFile = 0
        self.userDataCharacteristic = "2a9a"   #"00002a9a-0000-1000-8000-00805f9b34fb"

    async def scanAndConnect(self):
        await self.x2Ble.scan()
        # await self.x2Ble.scanAndConnect()

    def parseFileInfo(self, data, packetLen):
        fSize = struct.unpack("<I", data[:4])[0]
        self.totalBytesThisFile = fSize
        fName = data[4:packetLen].decode("ascii")
        return fSize, fName

    def parseFilePart(self, data, packetLen):
        chunkNo = struct.unpack("<I", data[:4])[0]
        chunkData = data[4:packetLen]
        return chunkNo, chunkData
    
    def parseHeader(self, data: bytearray):
        data = bytes(data)
        if data[0] != self.composer.HEADER_ID_COMMAND:
            Logger.info("Bad packet")
            return
        dataT = int(data[1])
        packetLen = struct.unpack("<H", data[2 : 2 + 2])[0]
        crcRead = struct.unpack("<H", data[packetLen + 4 : packetLen + 4 + 2])[0]
        crcCalc = self.composer.crc16(data[: packetLen + 4], 0, packetLen + 4)
        # Logger.info(
        #     f": dType {dataT}, pLen {packetLen} crcRead {crcRead}, crcCalc {crcCalc}"
        # )
        if crcRead != crcCalc:
            Logger.error(f"Checksum does not check out")
        if dataT == self.DATA_TYPE_FILEINFO:
            fSize, fName = self.parseFileInfo(data[4:], packetLen)
            Logger.info(f"File: {fName} {fSize}")
            if not fName:
                self.noMoreFiles = True
            self.filenameToFetch = fName
            self.fileSizeToFetch = fSize
            self.fetchingFileData = True
            self.downloadedSize = 0

            # await self.fetchFilePart()
        elif dataT == self.DATA_TYPE_FILEPART:
            chunkNo, chunkData = self.parseFilePart(data[4:], packetLen)
            Logger.info(f"\tchunkNo: {chunkNo}, chunkLen: {len(chunkData)}")
            if self.totalBytesThisFile > 0:
                perc = 100/self.totalBytesThisFile*self.downloadedSize
            else:
                perc = 0
            Logger.info(f"\t Uploading: {self.downloadedSize} / {self.totalBytesThisFile}, {perc}%")
                # Logger.info(f": chunkNo: {chunkNo}, chunkLen: {len(chunkData)}")
            if chunkData:
                # self.fileBuffer += chunkData
                self.fileBufferDict[chunkNo] = chunkData
                self.downloadedSize += len(chunkData)
            # else:
            #     self.fetchingFileData = False
            if self.downloadedSize >= self.fileSizeToFetch:
                self.fetchingFileData = False

            self.waitingForData = False

            # await self.fetchFilePart()
            pass
    
    def getFileData(self, characteristic, data: bytearray):
        # Logger.info("Received " + str(binascii.hexlify(data)))
        self.parseHeader(data)

    async def listAndFetch(self):
        # devices = self.x2Ble.listDevices()
        # for x2Name in devices:
        # x2 = devices[x2Name]

        x2 = self.x2Ble.x2["client"]
        services = x2.services
        for service in services.services.values():
            for characteristic in service.characteristics:
                if "fffb" in characteristic.uuid:
                    Logger.info(f"\tsubscribing service {service.uuid}")
                    self.ftpCharacteristic = characteristic
                    await self.x2Ble.subscribe(x2, characteristic, self.getFileData)
                    self.currentClient = {
                        "name": self.x2Ble.x2["name"],
                        "client": x2,
                        "sub": characteristic,
                    }
                    fileDir = f"./data/{str(self.currentClient['name'])}/"
                    if not os.path.exists(fileDir):
                        os.makedirs(fileDir)

    async def fetchNextFileInfo(self):
        await self.x2Ble.send_data(
            self.currentClient["client"],
            self.ftpCharacteristic,
            self.composer.composeX22Request(0, 1 << 5, struct.pack("B", 50)),
        )

    async def fetchFilePart(self):
        self.waitingForData = True
        await self.x2Ble.send_data(
            self.currentClient["client"],
            self.ftpCharacteristic,
            self.composer.composeX22Request(0, 1 << 5, struct.pack("B", 51)),
        )

    async def deleteCurrentFile(self):
        await self.x2Ble.send_data(
            self.currentClient["client"],
            self.ftpCharacteristic,
            self.composer.composeX22Request(0, 1 << 5, struct.pack("B", 52)),
        )

    def saveFile(self):
        # Clean the device name by replacing ':' with '_' and trimming whitespaces
        clean_device_name = re.sub(r"[ :]+", "_", str(self.currentClient['name'])).strip()
        
        # Construct the file directory path
        script_dir = Path(__file__).parent.absolute()  # Absolute script directory
        fileDir = script_dir / "../data" / clean_device_name
        fileDir.mkdir(parents=True, exist_ok=True)
        
        # Sort and concatenate the file buffer
        self.fileBufferDict = dict(sorted(self.fileBufferDict.items()))
        fileBuffer = bytearray()
        for chunkNo in self.fileBufferDict:
            fileBuffer += self.fileBufferDict[chunkNo]
        
        # Construct the file path and save the file
        filePath = fileDir / self.filenameToFetch
        with filePath.open("wb") as f:
            f.write(fileBuffer)
        Logger.info(f"Saved file to {filePath}")

    async def download(self):
        # await self.scanAndConnect()

        await self.listAndFetch()
        while not self.noMoreFiles:
            Logger.info("Download next file")
            self.filenameToFetch = ""
            self.fileSizeToFetch = 0
            self.downloadedSize = 0
            self.fetchingFileData = False
            self.waitingForData = False
            self.noMoreFiles = False
            # self.fileBuffer = bytearray()
            self.fileBufferDict = {}

            startts = datetime.datetime.now().timestamp()
            await self.fetchNextFileInfo()
            while not self.filenameToFetch:
                if self.noMoreFiles:
                    return
                await asyncio.sleep(0.1)

            while self.fetchingFileData:
                # await self.fetchFilePart()
                timeouts = 0
                await asyncio.sleep(0.1)

                while self.waitingForData:
                    # Logger.info(f"Fetching {self.waitingForData}")
                    await asyncio.sleep(0.1)
                    timeouts += 1
                    Logger.info(f"TimedOut {timeouts} time[s]")

                    if timeouts > 10:
                        Logger.info("TimedOut")
                        # await self.fetchFilePart()
            endts = datetime.datetime.now().timestamp()
            dt = endts - startts
            Logger.info(
                f"Fetched {self.filenameToFetch} at {self.fileSizeToFetch/dt} b/s"
            )
            await self.deleteCurrentFile()
            self.saveFile()
            await asyncio.sleep(1)
        await self.currentClient["client"].stop_notify(self.currentClient["sub"])

    async def showDeviceInfos(self):
        await self.x2Ble.showDeviceInfos()

    async def connectByAddress(self, address):
        await self.x2Ble.connectByAddress(address)

    async def connect(self, deviceName):
        await self.x2Ble.connect(deviceName)
    
    def getCharacteristic(self, services, uuid):  
        for service in services.services.values():
            for characteristic in service.characteristics:
                if uuid in characteristic.uuid:
                    return characteristic
                
    async def setup(self):
        x2 = self.x2Ble.x2["client"]
        services = x2.services
        characteristic = self.getCharacteristic(services,self.userDataCharacteristic)

        Logger.info(f"Setup device: {self.x2Ble.x2['name']}")
        bytestream = self.composer.composeX22Command(
            self.composer.IndexIMU,
            1 << 3,
            # imuConfigGyr4000DPS | imuConfigRaw200Hz | imuConfigAcc16GFsr | MAG_FSR_16GAUSS 
            #0x00060000 | 0x00000004 | 0x00000400,
            0x00060000  | 0x00000004 | 0x00000400 | 0x00400000
        )
        await self.x2Ble.send_data(
            x2, characteristic, bytestream
        )

        paramData = struct.pack(
            "<q", int(datetime.datetime.now().timestamp())
        )
        paramData += tzmap[tzlocal.get_localzone_name()].encode("ascii")
        paramData += b"\x00"
        bytestream = self.composer.composeX22Parameter(
            self.composer.SET_DATETIME, paramData
        )
        await asyncio.sleep(0.1)
        await self.x2Ble.send_data(
            x2, characteristic, bytestream
        )

        bytestream = self.composer.composeX22Parameter(
            self.composer.SET_OFFLINE_RECORDING_ENABLED, b"\x01"
        )
        await asyncio.sleep(0.1)
        await self.x2Ble.send_data(
            x2, characteristic, bytestream
        )

        bytestream = self.composer.composeX22Parameter(
            self.composer.SAVE_SETTINGS, b""
        )

        await asyncio.sleep(0.1)
        await self.x2Ble.send_data(
            x2, characteristic, bytestream
        )               

    async def saveSettings(self):
        x2 = self.x2Ble.x2["client"]
        services = x2.services
        characteristic = self.getCharacteristic(services,self.userDataCharacteristic)
        bytestream = self.composer.composeX22Parameter(
            self.composer.SAVE_SETTINGS, b""
        )
        await self.x2Ble.send_data(
            x2, characteristic, bytestream
        )               

    async def listAndSetDatetime(self):
        x2 = self.x2Ble.x2["client"]
        services = x2.services
        characteristic = self.getCharacteristic(services,self.userDataCharacteristic)
        bytestream = self.composer.composeX22Command(
            self.composer.IndexIMU,
            1 << 3,
            # imuConfigGyr4000DPS | imuConfigRaw200Hz | imuConfigAcc16GFsr
            0x00060000 | 0x00000004 | 0x00000400,
        )
        await self.x2Ble.send_data_with_response(
            x2, characteristic, bytestream
        )

        paramData = struct.pack(
            "<q", int(datetime.datetime.now().timestamp())
        )
        paramData += tzmap[tzlocal.get_localzone_name()].encode("ascii")
        paramData += b"\x00"
        bytestream = self.composer.composeX22Parameter(
            self.composer.SET_DATETIME, paramData
        )
        await asyncio.sleep(0.1)
        await self.x2Ble.send_data_with_response(
            x2, characteristic, bytestream
        )

        bytestream = self.composer.composeX22Parameter(
            self.composer.SET_OFFLINE_RECORDING_ENABLED, b"\x01"
        )
        await asyncio.sleep(0.1)
        await self.x2Ble.send_data_with_response(
            x2, characteristic, bytestream
        )

    async def setOfflineRecording(self, client, characteristic, setTo):
        bytestream = self.composer.composeX22Parameter(
            self.composer.SET_START_OFFLINE_RECORDING, struct.pack("B", setTo)
        )
        await self.x2Ble.send_data(client, characteristic, bytestream)

    async def startOfflineRecording(self):
        x2 = self.x2Ble.x2["client"]
        services = x2.services
        characteristic = self.getCharacteristic(services,self.userDataCharacteristic)
        await self.setOfflineRecording(x2, characteristic, 1)

    async def stopOfflineRecording(self):
        x2 = self.x2Ble.x2["client"]
        services = x2.services
        characteristic = self.getCharacteristic(services,self.userDataCharacteristic)
        await self.setOfflineRecording(x2, characteristic, 0)
    
    async def eraseFlash(self):
        x2 = self.x2Ble.x2["client"]
        services = x2.services
        characteristic = self.getCharacteristic(services,self.userDataCharacteristic)
        await self.x2Ble.send_data(x2,
            characteristic,
            self.composer.composeX22Request(0, 1 << 5, struct.pack("B", 53)),
        )

    async def reboot(self):
        x2 = self.x2Ble.x2["client"]
        services = x2.services
        characteristic = self.getCharacteristic(services,self.userDataCharacteristic)
        await self.x2Ble.send_data(x2,
            characteristic,
            self.composer.composeX22Request(0, 1 << 5, struct.pack("B", 2)),
        )

    async def configWifi(self, WifiName,WifiPW):
        configWifiCmd =  self.composer.composeWifiCred(WifiName,WifiPW)
        x2 = self.x2Ble.x2["client"]
        services = x2.services
        characteristic = self.getCharacteristic(services,self.userDataCharacteristic)
        await self.x2Ble.send_data(x2,
            characteristic,
            configWifiCmd
        )
        Logger.info("Wifi configured")

    async def shutdown(self):
        x2 = self.x2Ble.x2["client"]
        services = x2.services
        characteristic = self.getCharacteristic(services,self.userDataCharacteristic)
        await self.x2Ble.send_data(x2,
            characteristic,
            self.composer.composeX22Request(0, 1 << 5, struct.pack("B", 1)),
        )

    async def factory_reset(self):
        x2 = self.x2Ble.x2["client"]
        services = x2.services
        characteristic = self.getCharacteristic(services,self.userDataCharacteristic)
        await self.x2Ble.send_data(x2,
            characteristic,
            self.composer.composeX22Request(0, 1 << 5, struct.pack("B", 3)),
        )
                    
                    
    async def scan(self):
        await self.x2Ble.scan()

    async def connectAndSetup(self, deviceName):
        await self.connect(deviceName)
        await asyncio.sleep(2)
        await self.setup()
        # await self.scanAndConnect()
        # await self.listAndSetDatetime()

    async def disconnect(self):
        await self.x2Ble.disconnect()


# if __name__ == "__main__":
#     x2Dldr = AxiamoX2BLEOfflineRecorder()
#     asyncio.run(x2Dldr.connectAndSetup())
#     # asyncio.sleep(10)
