from bleak import BleakScanner
from axiamo_lib.AxiamoX2FtpDownloader import FTPDownloader
import threading
import time
import json
class BLEFTPDownloader:
    def __init__(self):
        self.active_downloads = {}
        self.active_threads = {}
        self.bleClients = {}

        self.expectedFirmware = "1.7"


    def check_active_downloads(self, address, name):
        if name in self.active_downloads:
            return True
        else:
            self.spawnDownLoader(address,name)           

    def spawnDownLoader(self, address, name):
        print(f" - {name} is starting to download from {address}.")
        
        firmwareUpdate =  False 
        self.active_downloads[name] = FTPDownloader(address, "axiamo", "axiamo", "rawdata", name,firmwareUpdate)
        self.active_threads[name] = threading.Thread(target = self.active_downloads[name].run)
        self.active_threads[name].start()

    def check_downloads_still_active(self):
        print(f"Checking if downloads are still active")
        downLoadsToDelete = []
        for name in self.active_downloads:
            if self.recycle_active_downloads(name):
                downLoadsToDelete.append(name)
        
        for name in downLoadsToDelete:               
                del self.active_downloads[name]
                del self.active_threads[name]    


    def recycle_active_downloads(self, name):
        result = False
        if name in self.active_downloads:
            print(f"checking download: {name}")
            if not self.active_downloads[name].running:
                print(f" - {name} is no longer being downloaded.")
                result = True
        return result

if __name__ == "__main__":
    downloader = BLEFTPDownloader()

    with open("configuration.json", 'r') as file:
        config_data = json.load(file)

    name = config_data.get("deviceAlias")
    address = config_data.get("ip")

    while(True):
        print(f"Axiamo X2 Standalone StationController running {time.time()}")
        downloader.check_active_downloads(address,name)
        downloader.check_downloads_still_active()
        time.sleep(1)
