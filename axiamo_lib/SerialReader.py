import serial.tools.list_ports
import subprocess
from axiamo_lib.BaseLogger import Logger
import threading 
import time
import sys
import datetime
from axiamo_lib.LogFileParser import LogFileParser
import os
    
class SerialReader():
    
    def __init__(self,port,silent=False):
        self.ser = serial.Serial(port=port, baudrate=115200, timeout=1, xonxoff = False, rtscts = False,dsrdtr = False)
        self.databuffer = bytearray()
        self.parser = LogFileParser()
        self.port = port
        self.line_buffer = []
        self.ser.rts = 0
        self.ser.dtr = 0
        self.resetTimeout = .1
        self.logPath = "Logs/RawLogs/"
        self.logFileName=self.logPath + self.create_log_filename()    
        self.ensure_directory_exists(self.logPath)
        self.logFile = self.open_log_file(self.logFileName)
        self.silent = silent




    def ensure_directory_exists(self,directory_path):
        if not os.path.exists(directory_path):
            try:
                os.makedirs(directory_path)
                print(f"Created directory: {directory_path}")
            except OSError as e:
                print(f"Error creating directory: {e}")

    def create_log_filename(self):
        portFilePart=self.port.replace("/",".")
        current_datetime = datetime.datetime.now()
        formatted_datetime = current_datetime.strftime("%Y_%m:%d_%H_%M_%S")
        log_filename = f"log_{portFilePart}_{formatted_datetime}.txt"
        return log_filename
    
    def open_log_file(self,filename):
        try:
            self.file = open(filename, "a")  # Open the file in append mode
            return self.file
        except FileNotFoundError:
            print(f"File '{filename}' not found.")
            return None

    def append_line_to_file(self, line):
        if self.file:
            try:
                self.file.write(line.decode("utf8"))  # Append a line to the file
            except Exception as e:
                print(f"An error occurred while writing to the file: {e}")
            self.file.flush()

    def start(self):
        self.running = True
        self.readThread = threading.Thread(target=self.mainTask)
        self.readThread.start()
    
    def stop(self):
        self.running = False
        time.sleep(2)
        self.ser.close()

    def reboot(self,ToBootLoader = False):
        # RTS 1 -> 0 = reboot
        # DTR  1 on rebott = boot to bootloader
        self.ser.rts = 0
        self.ser.dtr = 0
        
        if ToBootLoader:
            time.sleep(self.resetTimeout)
            self.ser.rts = 1
            time.sleep(self.resetTimeout)
            self.ser.dtr = 1
            time.sleep(self.resetTimeout)
            self.ser.rts = 0
            self.ser.dtr = 0
        else:
            time.sleep(self.resetTimeout)
            self.ser.rts = 1
            time.sleep(self.resetTimeout)
            self.ser.rts = 0

    def extract_lines(self,databuffer, line_buffer):
        newline = b"\r\n"
        newline_index = databuffer.find(newline)
        numberOfLines = 0 
        while newline_index != -1:
            try:
                line = databuffer[:newline_index + 2]  
                databuffer = databuffer[newline_index + 2:] 
                line_buffer.append(line.decode("utf8"))
                self.parser.parseline(line)
                newline_index = databuffer.find(newline)
                self.append_line_to_file(line)
                numberOfLines += 1
                #Logger.info(f"{len(line)} bytes | {line}")
            except Exception as ex:
                print(f"exception: {ex}")

        return databuffer, numberOfLines
    
    def mainTask(self):
        self.reboot()
        while self.running :
    
            # Read a line of data from the serial port
            #line = self.ser.readline()
            try:
                while self.ser.in_waiting > 0:
                    self.databuffer += self.ser.read()
            except Exception as ex:
                print(f"exception: {ex}")

            self.databuffer, numberOfLines = self.extract_lines(self.databuffer, self.line_buffer)

            if numberOfLines > 0:
                for i in range(-numberOfLines,0):
                    line = self.line_buffer[i]
                    if not self.silent:
                        Logger.info(f"{len(line)} bytes | {line}")      
                        Logger.info(self.parser.getInfo())
            time.sleep(.5)

            
if __name__ == '__main__':
    if len(sys.argv) < 2:
        #linux:
        port = "/dev/ttyUSB0"
        # windows:
        port = "com4"
    else:
        port = sys.argv[1]
    ser = SerialReader(port)
    ser.start()
    while True:
        time.sleep(1)
