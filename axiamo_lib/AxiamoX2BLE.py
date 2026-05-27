import asyncio
import bleak
import binascii
from bleak import BleakScanner, BleakClient
from axiamo_lib.BaseLogger import Logger

class AxiamoX2Ble():
    USER_DATA_CHAR = "00002a9a-0000-1000-8000-00805f9b34fb"
    def __init__(self):
        self.scanned_devices = []
        self.scanned_x2s = []
        self.x2s = []
        self.bytesReceived = []

    async def scanForDevices(self):
        self.listServices = False
        Logger.info("scanning for BLE devices")
        self.scanned_devices = await bleak.BleakScanner.discover(5);
        self.scanned_x2s=[]
        self.x2s=[]

        if len(self.scanned_devices) == 0:
            raise bleak.exc.BleakError("no devices found")
        self.scanned_devices.sort(key=lambda device: -device.rssi)
        
        for device in self.scanned_devices:
            if device.name and device.name.find("AxiamoX2") >= 0:
                        Logger.info("Found AxiamoX2 device:")
                        Logger.info(f"{device.name} {device.rssi}dB")
                        self.scanned_x2s.append(device)
        Logger.info(f"Scan done, found devices: {len(self.scanned_x2s)} {self.scanned_x2s}")

    async def connectDevice(self, device):
        x2Client = None
        try:
            x2Client = BleakClient(device, disconnected_callback = self.handle_disconnect)
            Logger.info(f"Connecting to {x2Client} via BLE.")
            await x2Client.connect()
            Logger.info("Axiamo X2 connected.")
            self.x2s.append(x2Client)
            if self.listServices:
                services = await x2Client.get_services()
                for service in services.services.values():
                    Logger.info(f"  service {service.uuid}")
                    for characteristic in service.characteristics:
                        Logger.info(f"  characteristic {characteristic.uuid} {hex(characteristic.handle)} ({len(characteristic.descriptors)} descriptors)")                   
                        
        except bleak.exc.BleakError as e:
            Logger.error(f"  error {e}")
            await asyncio.sleep(10)
        
        return x2Client               


    def handle_disconnect(self,_: BleakClient):
        Logger.info("Device was disconnected, goodbye.")

    async def handle_rx(self,dev: int, data: bytearray):
        #self.bytesReceived += len(data)
        Logger.info(f"Received from {dev} {binascii.hexlify(data)}")        
    
    async def start_receiving(self,x2):
        try:
            client = x2
            await client.start_notify(self.USER_DATA_CHAR, self.handle_rx)
        except Exception as e:
            Logger.error(f"  error {e}")

    async def send_data(self,client,data):
        await client.write_gatt_char(self.USER_DATA_CHAR, data,True)

    def listAvailableDevices(self):
        return self.scanned_x2s

    def listConnectedDevices(self): 
        return self.x2s

