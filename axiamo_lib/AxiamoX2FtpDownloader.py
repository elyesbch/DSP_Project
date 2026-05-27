import ftplib
import os
import time
from re import findall
from subprocess import Popen, PIPE

class FTPDownloader:
    def __init__(self, server, username, password, download_path,devName,firmwareUpdate):
        self.server = server
        self.username = username
        self.password = password
        self.devName = devName.replace(":","_")
        self.download_path = f"{download_path}/{self.devName}"
        self.firmwareUpdate = firmwareUpdate
        self.connectTimeout = 10
        self.running = True
        self.ftp= None
        
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)
    
    def ping(self, host, ping_count):
        result = False
        ping_test = False
        for ip in host:
            data = ""
            print(f"Pinging: ", ip)
            output = Popen(["ping", ip, "-n", str(ping_count) ,"-w","5"], stdout=PIPE, encoding="utf-8")
            #output= Popen(f"ping {ip} -n {ping_count}", stdout=PIPE, encoding="utf-8")
            
            for line in output.stdout:
                print(f"Answer: {line}")
                data = data + line
                ping_test = findall("ttl", data)

            if ping_test:
                result = True
                print(f"{ip} : Successful Ping")
            else:
                result = False
                print(f"{ip} : Failed Ping")
        return result

    def run(self):
        success = False
        connected = False
        downloaded = False
        pingable =True
        firmwareUploaded = False

        while(not success):
            while(not connected):
                try:
                    self.connect_ftp()
                    connected = True
                except Exception as e:
                    print(f"\nError connecting {e}")    

                try: 
                    self.download_files()
                    downloaded = True
                except Exception as e:
                    print(f"\nError downloading {e}")
            
            success = connected and downloaded
            
            try: 
                connected = False
                downloaded = False
                self.close_ftp()
            except Exception as e:
                print(f"\nError closing ftp connection {e}")

        print(f"FTP download complete? {success}")
        self.running=False
        
    def connect_ftp(self):
        try:
            self.ftp = ftplib.FTP(self.server, timeout=self.connectTimeout)
            self.ftp.login(self.username, self.password)
            print("Connected to the FTP server.")
        except Exception as ex:
            if ex.errno==113:
                print(f"Sensor seems offline")
            else:
                print(f"{ex}")

    def list_files(self):
        files = []
        if self.ftp:
            files = self.ftp.nlst()
            print("Files on the FTP server:")
            for file in files:
                print(file)
        return files
    
    def upload_firmware(self):
        if not os.path.exists("OTA/X22-Firmware.bin"):
            return        

        local_file_path = "OTA/X22-Firmware.bin"

        file_size = os.path.getsize(local_file_path)

        # Function to track upload progress
        def upload_progress(block):
            nonlocal uploaded_bytes
            uploaded_bytes += len(block)
            progress_percentage = (uploaded_bytes / file_size) * 100
            print(f"\rUploaded {uploaded_bytes} of {file_size} bytes ({progress_percentage:.2f}%)", end="")

        uploaded_bytes = 0  # Initialize uploaded bytes to 0 before starting upload

        with open(local_file_path, 'rb') as file:
            remote_file_path = os.path.basename(local_file_path)
            # Using a lambda to pass the block to the upload_progress function
            self.ftp.storbinary(f'STOR {remote_file_path}', file, 1024, upload_progress)
            print(f"\nUploaded {local_file_path} to {remote_file_path} on the FTP server.")
    
    def ensure_dir_for_file(self,file_path):
        # Extract the directory part from the file path
        dir_name = os.path.dirname(file_path)
        
        # Create the directory if it doesn't exist, also create any intermediate directories as needed
        os.makedirs(dir_name, exist_ok=True)

    def download_files(self):
        files = self.list_files()
        for file in files:
            if(".bd" in file):
                try:
                    local_filename = os.path.join(self.download_path, file)
                    local_filename_tmp = local_filename + ".tmp"
                    self.ensure_dir_for_file(local_filename_tmp)

                    f = open(local_filename_tmp, 'wb')
                    start_time = time.time()
                    def handle_binary_data(block):
                        f.write(block)
                        print(f"\rDownloading: {file} - {f.tell()} bytes", end="")

                    print(f"\rDownload: {file}")                        
                    self.ftp.retrbinary('RETR ' + file, handle_binary_data)
                    print(f"\rDone downloading: {file}")                                            
                    f.close()
                    end_time = time.time()
                    download_time = end_time - start_time
                    file_size = os.path.getsize(local_filename_tmp)
                    download_speed = file_size / download_time
                    
                    print(f"\nDownloaded: {file} in {download_time:.2f} seconds at {download_speed:.2f} bytes/second")
                    self.ftp.delete(file)
                    
                    os.rename(local_filename_tmp,local_filename)
                    print(f"\nDeleted: {file} from the FTP server.")

                except Exception as e:
                    print(f"\nError downloading {file}: {e}")
                    if '451' in e.args[0]:
                        print(f"File {file} has zero size, delete")
                        self.ftp.delete(file)

    
    def close_ftp(self):
        if self.ftp:
            self.ftp.quit()
            print("Connection closed.")
