import serial.tools.list_ports
from axiamo_lib.BaseLogger import Logger
import time
from axiamo_lib.SerialReader import SerialReader
import os
import re
import datetime
import shutil
import json
from datetime import datetime
import pandas as pd

class DeviceInfoDumper:
    def __init__(self):
        self.serialReaders = []
        self.NoWiFiIsOk = False
        self.attributesToCheck =["ip"]        

    def __del__(self):
        print('Destructor called, DeviceInfoDumper gets deleted.')
        for s in self.serialReaders:
            s.stop()
        self.serialReaders = []
        print('DeviceInfoDumper stopped.')

    def enumerate(self):
        Logger.info("DeviceInfoDumper enumerates ports")

        for s in self.serialReaders:
            s.stop()

        self.serialReaders = []
        time.sleep(5)

        self.allports = [comport.device for comport in serial.tools.list_ports.comports()]
        self.comports = [comport.device for comport in serial.tools.list_ports.comports() if "USB" in comport.device or  "COM3" in comport.device or "usbserial" in comport.device]
        Logger.info(f"allports: { self.allports}")
        Logger.info(f"comports: {self.comports}")

        for port in self.comports:
            Logger.info(f"X22 at {port}")
            ser = SerialReader(port,silent=True)
            ser.start()
            ser.reboot()
            self.serialReaders.append(ser)

    def ensure_directory_exists(self,directory_path):
        if not os.path.exists(directory_path):
            try:
                os.makedirs(directory_path)
                print(f"Created directory: {directory_path}")
            except OSError as e:
                print(f"Error creating directory: {e}")

    def create_log_foldername(self):
        current_datetime = datetime.now()
        formatted_datetime = current_datetime.strftime("%Y_%m:%d_%H_%M_%S")
        log_foldername = f"Logs/"

        return log_foldername          

    def saveDeviceInfo(self, deviceInfo):
        devices_folder = os.path.join(self.create_log_foldername(), "Devices")
        self.ensure_directory_exists(devices_folder)

        for device in deviceInfo.values():
            if 'bleMAC' in device and device['bleMAC'] is not None and 'wifiMac' in device and device['wifiMac']:
                mac_address = device['bleMAC'].split()[-1]  # Assumes the MAC address is the last part of the 'bleMAC' string
                filename = f"AxiamoX22_log{re.sub('[^a-zA-Z0-9]', '', mac_address)}.json"  # Remove special characters to make it filesystem-friendly

                device_file_path = os.path.join(devices_folder, filename)
                with open(device_file_path, 'w') as file:
                    json.dump(device, file, indent=4)
                    Logger.info(f"Saved device info for {mac_address} in {device_file_path}")
            
            Logger.info(f"{deviceInfo.values()}")

    def storeResultPandas(self, deviceInfo):
        #save all device info as pandas dataframe

        for device in deviceInfo.values():
            #get dataframe from dict device
            df = pd.DataFrame.from_dict(device, orient='index')
            #display the dataframe
            print(df)
            #save as pdf file
            


    def storeResult(self):
        source_folder = "Logs/"
        destination_folder = self.create_log_foldername()

        self.ensure_directory_exists(destination_folder)

        # Attempt to load existing overview data
        overView_path = os.path.join(destination_folder, "overview.json")
        if os.path.exists(overView_path):
            with open(overView_path, 'r') as file:
                overView = json.load(file)
        else:
            overView = {}

        # Assuming self.serialReaders is already defined and populated elsewhere
        for s in self.serialReaders:
            devInfo = s.parser.getInfo()  # Assuming this gets the new data to update
            Logger.info(f"{s.port}  {devInfo}")
            overView[s.port] = devInfo  # Update or add new device info
            self.saveDeviceInfo({s.port: devInfo})
            self.storeResultPandas({s.port: devInfo})

        # Write updated overView back to overview.json
        with open(overView_path, 'w') as file:
            json.dump(overView, file, indent=4)
        Logger.info(f"Updated overview.json in {destination_folder}")

        # Move files after updating overview to ensure overview is always up-to-date
        for filename in os.listdir(source_folder):
            source_file = os.path.join(source_folder, filename)
            
            if os.path.isfile(source_file):
                destination_file = os.path.join(destination_folder, filename)
                shutil.move(source_file, destination_file)
                print(f"Moved: {filename} to {destination_folder}")
            else:
                print(f"Skipped: {filename} (subfolder)")

        Logger.info(f"Result stored in {destination_folder}")

    def nowInSeconds(self):
        utc_datetime = datetime.utcnow()
        return utc_datetime.timestamp()

    def stop(self):
        for s in self.serialReaders:
            s.stop()
        self.serialReaders = []

    def mainTask(self,durationInMinutes=1,AutoRepeat=True):

        timeStart = self.nowInSeconds()
        timeElapsed = 0 
        durationInSeconds = durationInMinutes*60
        
        while True:
            self.enumerate()
            runtime = 0
            rtTolerance = 10
            AllGood = True
            TimeAfterError = 0
            for s in self.serialReaders:
                s.reboot()


            while AllGood and timeElapsed < durationInSeconds or TimeAfterError > 0:
                for s in self.serialReaders:
                    devInfo = s.parser.getInfo()
                    Logger.info(f"time elapsed: {timeElapsed} / {durationInSeconds} s")
                    Logger.info(f"{s.port}  {devInfo}")
                    
                    if 'status' in devInfo and devInfo['status'] != None:
                         if 'runtime' in devInfo['status'] and devInfo['status']['runtime'] != None:
                             rt = int(devInfo['status']['runtime'])
                             if rt >= (runtime - rtTolerance) * 1000  and rt <= (runtime + rtTolerance) * 1000:
                                 pass
                             else:
                                AllGood = False
                                Logger.error(f"device at port {s.port} and status {rt} seems to have an issue... check: {s.logFileName}")
                                Logger.info(f"runtime at: {runtime*1000}, device runtime: {rt}")
                                s.parser.result ="Fail"
                                TimeAfterError = 10
                                
                time.sleep(1)
                timeElapsed = self.nowInSeconds() - timeStart
                Logger.info(f"==== {timeElapsed} / {durationInSeconds} s ======")
                runtime += 1
                if TimeAfterError > 0:
                    TimeAfterError -= 1

                self.storeResult()
            

            if not AutoRepeat:
                break

        Logger.info(f"---- Result: {AllGood} -----------")
        for s in self.serialReaders:
            devInfo = s.parser.getInfo()
            Logger.info(f"{s.port}  {devInfo}")

        Logger.info("Test done, returning from maintask")
        return AllGood
            

if __name__ == '__main__':
    dst = DeviceInfoDumper()
    while True:
        result = dst.mainTask(1,False)
    