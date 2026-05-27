import os
import re
from axiamo_lib.BaseLogger import Logger
from axiamo_lib.bluetooth_interface.util.dataParser import Parser
import numpy as np
import pickle
from datetime import datetime
from axiamo_lib.FsrConstants import FullScaleRangeConstants as fsr
import plotly.graph_objects as go
from plotly.subplots import make_subplots


class DumpFileParser:
    def __init__(self):
        # Automatically set directory path to look one folder above the script's location
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.directory_path = os.path.abspath(os.path.join(script_dir, "..", "rawdata"))
        print(f"Looking for files in: {self.directory_path}")

    def log_info(self, *args, **kwargs):
        message = ' '.join(map(str, args))
        Logger.info(message, **kwargs)

    def storeParserBuffer(self, devName, timestamp, data):
        self.deviceData = {}
        # Data processing...
        acc = np.array(data.dataDict["ImuAccRaw"].data).T
        gyr = np.array(data.dataDict["ImuGyrRaw"].data)[1:4].T
        mag = np.array(data.dataDict["ImuMagRaw"].data)[1:4].T
        bat = np.array(data.dataDict["Battery"].data).T
        temp = np.array(data.dataDict["ImuTemp"].data).T
        
        # Sanitize device name
        sanitized_devName = re.sub(r"[ :]+", "_", devName).strip()
        
        self.deviceData[sanitized_devName] = {
            'x_vals': list(acc[:, 0]),
            'y_vals_acc': acc[:, 1:4] * fsr.accFactor,
            'y_vals_gyr': gyr * fsr.gyroFactor,
            'y_vals_mag': mag * fsr.magFactor,
            'y_vals_bat': bat,
            'y_vals_temp': temp
        }
        
        dt_object = datetime.utcfromtimestamp(timestamp)
        formatted_date = dt_object.strftime("%Y%m%d_%H%M%S")
        folder = os.path.join(self.directory_path, sanitized_devName)
        
        if not os.path.exists(folder):
            os.makedirs(folder)
        
        FullName = os.path.join(folder, f"{formatted_date}.pickle")
        with open(FullName, 'wb') as f:
            pickle.dump(self.deviceData, f)
        
        Logger.info(f"Saved data to file: {FullName}")
    
    def find_and_parse_files(self):
        Logger.info(f"Looking for files in directory: {self.directory_path}")
        
        for root, dirs, files in os.walk(self.directory_path):
            Logger.info(f"Found {files} files in directory: {root}")
            for file in files:
                if file.endswith("_rec.bd"):
                    file_path = os.path.join(root, file)
                    self.parse_and_store(file_path)          

    def parse_and_store(self, file_path):
     
           
        pattern =r'(\d+)_rec\.bd$'
        matchIdentifier = re.search(pattern, file_path)
        
        device_name =""
        timestamp = 0

        if matchIdentifier:
            Logger.info(f"file ending matches: {file_path}")
            device_name = "X22"
            timestamp = int(matchIdentifier.group(1))

        if device_name == "":
            return "no valid device name found in file name"
      
        file = open(file_path, "rb")
        binary_data = file.read()
        file.close()
        self.rawParser = Parser(logf=self.log_info)
        self.rawParser.parseStream(binary_data)
        self.storeParserBuffer(device_name, timestamp, self.rawParser.dataBuffer)
        
        processed_folder = os.path.join(self.directory_path, "processed")
        if not os.path.exists(processed_folder):
            os.makedirs(processed_folder)
        os.rename(file_path, os.path.join(processed_folder, os.path.basename(file_path)))

if __name__ == "__main__":
    parser = DumpFileParser()
    parser.find_and_parse_files()
