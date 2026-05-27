from axiamo_lib.BaseLogger import Logger
import re
class LogFileParser:
    def __init__(self):
        self.bleMac = None
        self.wifiMac = None        
        self.status = None
        self.crystalCalibrated = None
        self.ImuInit = None
        self.MagInit = None
        self.POSTresult = None
        self.WiFiConnected = None        
        self.ip = None
        self.nocrash = None
        self.chipModel = None
        self.pSRAMSize = None
        self.flashFree = None
        self.flashTotal = None

        self.result = "Pass"
            
        self.checks = [
            {'attrib': 'ip', 'function': self.extractIp, 'onetime': False},
            {'attrib': 'bleMac', 'function': self.extract_mac_address, 'onetime': True}             
        ]
        # self.checks = [
        #     {'attrib': 'status', 'function': self.parse_status, 'onetime': False},
        #     {'attrib': 'bleMac', 'function': self.extract_mac_address, 'onetime': True}, 
        #     {'attrib': 'wifiMac', 'function': self.extract_wifi_mac, 'onetime': True},
        #     {'attrib': 'crystalCalibrated', 'function': self.extract_crystal_calib, 'onetime': True},
        #     {'attrib': 'ImuInit', 'function': self.checkImuInit, 'onetime': True},  
        #     {'attrib': 'MagInit', 'function': self.checkMagInit, 'onetime': True},  
        #     {'attrib': 'POSTresult', 'function': self.checkPOST, 'onetime': True},  
        #     {'attrib': 'WiFiConnected', 'function': self.checkWifiConnection, 'onetime': True},              
        #     {'attrib': 'ip', 'function': self.extractIp, 'onetime': True},              
        #     {'attrib': 'nocrash', 'function': self.checkNoCrash, 'onetime': False},
        #     {'attrib': 'chipModel', 'function': self.extract_chip_model, 'onetime': True},
        #     {'attrib': 'pSRAMSize', 'function': self.extract_psram_size, 'onetime': True},
        #     {'attrib': 'flashFree', 'function': self.extract_flash_free, 'onetime': True},
        #     {'attrib': 'flashTotal', 'function': self.extract_flash_total, 'onetime': True}
        # ]
        self.results = []
        
    def checkNoCrash(self,line):
        pattern = r'CPU halted.'
        match = re.search(pattern, line)
        if match:
            return False
        else:
            return True

    def checkImuInit(self,line):
        pattern = r'IMU success: 1'
        match = re.search(pattern, line)
        if match:
            return True
        else:
            return None

    def checkMagInit(self,line):
        pattern = r'MAG success: 1'
        match = re.search(pattern, line)
        if match:
            return True
        else:
            return None
        
    def checkPOST(self,line):
        pattern = r'Power On Self Test result: PASS'
        match = re.search(pattern, line)
        if match:
            return True
        else:
            return None

    def checkWifiConnection(self,line):
        pattern = r'WiFi connected'
        match = re.search(pattern, line)
        if match:
            return True
        else:
            return None

    def extractIp(self,line):
        pattern = r' X22: IP: (\d*.\d*.\d*.\d*)'                
        match = re.search(pattern, line)
        ip = match.group(1) if match else None
        return ip

    def extract_wifi_mac(self, line):
        pattern = r'wifi:mode : sta \(([0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2})\)'
        match = re.search(pattern, line)
        if match:
            return match.group(1)
        else:
            return None


    def parseline(self,line):
        line = line.decode("utf8")
        markDone = []

        for i in self.checks:
            val = i['function'](line)
            #Logger.info(f"----Check: {i['attrib']} value: {val}")
            if val != None:
                setattr(self,i['attrib'],val)
                if i['onetime']:
                    markDone.append(i)
        
        for j in markDone:
            self.results.append(j)
            self.checks.remove(j)

        
    def parse_status(self,input_string):
        # Define regular expressions to match each value
        runtime_pattern = r'\((\d+)\)'
        voltage_pattern = r'U: (\d+mV)'
        temperature_pattern = r'T: (\d+\.\d+°C)'
        current_pattern = r'I: (\d+mA)'
        soc_pattern = r'SoC: (\d+)%'

        # Use regular expressions to find and extract values
        runtime_match = re.search(runtime_pattern, input_string)
        voltage_match = re.search(voltage_pattern, input_string)
        temperature_match = re.search(temperature_pattern, input_string)
        current_match = re.search(current_pattern, input_string)
        soc_match = re.search(soc_pattern, input_string)

        # Extract the matched values
        runtime = runtime_match.group(1) if runtime_match else None
        voltage = voltage_match.group(1) if voltage_match else None
        temperature = temperature_match.group(1) if temperature_match else None
        current = current_match.group(1) if current_match else None
        soc = soc_match.group(1) if soc_match else None
        success = soc != None
        if success:
            return {
                "runtime": runtime,
                "batteryVoltage": voltage,
                "temperature": temperature,
                "current": current,
                "stateOfCharge": soc
            }
        else:
            return None

    def extract_mac_address(self, input_string):
        mac_pattern = r'Set device name: X22\s*([0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2})'
        cleaned_input = re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', input_string)
        match = re.search(mac_pattern, cleaned_input)
        
        if match:
            mac_address = match.group(1)
            return mac_address
        else:
            return None

        
    def extract_crystal_calib(self,input_string):
        pattern = r'External 32kHz'
        match = re.search(pattern, input_string)
        if match:
            return True
        else:
            return None


    def extract_chip_model(self, line):
        pattern = r"This chip is (\w+-\w+-\w+-\w+)"
        match = re.search(pattern, line)
        if match:
            return match.group(1)
        else:
            return None

    def extract_psram_size(self, line):
        pattern = r"SPI ram: (\d+)"
        match = re.search(pattern, line)
        if match:
            return match.group(1) + " kb"
        else:
            return None

    def extract_flash_free(self, line):
        pattern = r"FlashFree: (\d+)"
        match = re.search(pattern, line)
        if match:
            return match.group(1) + " kb"
        else:
            return None

    def extract_flash_total(self, line):
        pattern = r"FlashTotal: (\d+)"
        match = re.search(pattern, line)
        if match:
            return match.group(1) + " kb"
        else:
            return None

    def getInfo(self):
        self.info = {
            "ip": self.ip,
            "bleMac":self.bleMac
        }
        return self.info