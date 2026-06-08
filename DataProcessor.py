import pickle
import os
import fnmatch
import pandas as pd
import numpy as np
from math import pi
from ahrs.filters import *
from ahrs.filters import Tilt
from ahrs.filters import AngularRate
from axiamo_lib.BaseLogger import Logger
from axiamo_lib.DataSet import DataSet
from axiamo_lib.Visualizer import Visualizer
from axiamo_lib.ellipsoid import EllipsoidTool
from axiamo_lib.DumpFileParser import DumpFileParser
import matplotlib.pyplot as plt

class DataProcessor:
    def __init__(self, datafolder = "rawdata"):
        self.datafolder = datafolder
        self.fs = 200
        self.quats={}
        self.ds = None
        self.degreeToRad = 2*pi/360
        self.gToMs = 9.81
        self.gaussTo_uTesla = 100
        self.calibrationData = {'center':np.zeros(3),'radii':np.ones(3),'rotation':np.eye(3)}  
        pass

    def loadRawData(self,filename):
        #Todo: Check if / why the accscale is needed and apply it consistently to the data 
        file = open(filename,'rb')
        self.data = pickle.load(file)

    def loadRawDataDevice(self,dev):
        startIndex = 0
    
        devData = self.data[dev]
        sample = np.array(devData['x_vals'][startIndex:])
        acc = devData['y_vals_acc'][startIndex:]
        gyr = devData['y_vals_gyr'][startIndex:]
        mag = devData['y_vals_mag'][startIndex:]
        bat = devData['y_vals_bat'][startIndex:]
        temp = devData['y_vals_temp'][startIndex:]

        #Logger.info(f"lens: {len(sample)}  {len(acc)}    {len(gyr)} {len(mag)}")
        t =  np.array([ts / self.fs for ts in sample])
        batT = np.array([ts[0] / self.fs for ts in bat])
        
        if(len(t) > 0):
            t = t - t[0]

        if(len(batT) > 0):
            batT = batT - batT[0]
            
        accX = np.array([val[0] for val in acc])
        accY = np.array([val[1] for val in acc])
        accZ = np.array([val[2] for val in acc])
        gyrX = np.array([val[0] for val in gyr])
        gyrY = np.array([val[1] for val in gyr])
        gyrZ = np.array([val[2] for val in gyr])
        magX = np.array([val[0] for val in mag])
        magY = np.array([val[1] for val in mag])
        magZ = np.array([val[2] for val in mag])
        temp = np.array([val[1] for val in temp])

        batMa = np.array([val[1] for val in bat])
        batVolt = np.array([val[2] for val in bat])
        batPerc = np.array([val[3] for val in bat])

        maxLen = min([len(t), len(accX),len(accY),len(accZ),len(gyrX),len(gyrY),len(gyrZ),len(magX),len(magY),len(magZ)])
        maxLenBat = min([len(batT), len(batVolt),len(batMa),len(batPerc)])
        
        accData = {
        't':t[-maxLen:],
        'x':accX[-maxLen:],
        'y':accY[-maxLen:],
        'z':accZ[-maxLen:]
        }
        gyrData = {
        't':t[-maxLen:],
        'x':gyrX[-maxLen:],
        'y':gyrY[-maxLen:],
        'z':gyrZ[-maxLen:]
        }
        magData = {
        't':t[-maxLen:],
        'x':magX[-maxLen:],
        'y':magY[-maxLen:],
        'z':magZ[-maxLen:]
        }
        batData = {
        't':batT[-maxLenBat:],
        'mVolt':batVolt[-maxLenBat:],
        'mA':batMa[-maxLenBat:],
        'perc':batPerc[-maxLenBat:]
        }
        tempData = {
        't':t[-maxLen:],
        'temp':temp[-maxLen:]
        }

        self.acc = np.array([accData['x'],accData['y'],accData['z']]).T
        self.gyr = np.array([gyrData['x'],gyrData['y'],gyrData['z']]).T
        self.mag = np.array([magData['x'],magData['y'],magData['z']]).T
        self.temp = np.array([tempData['t'],tempData['temp']]).T
        self.bat = np.array([batData['t'], batData['mVolt'],batData['mA'],batData['perc']]).T

        self.dfAcc = pd.DataFrame(accData)
        self.dfGyr = pd.DataFrame(gyrData)
        self.dfMag = pd.DataFrame(magData)
        self.dfTemp =  pd.DataFrame(tempData)
        self.dfBat = pd.DataFrame(batData)

        self.updateDataSet()
    
    def loadAndApplyLastCalibration(self,dev):
        dev = dev.replace(" ","_")
        dev = dev.replace(":","_")
        calibrationFile = None

        if os.path.isfile(f"{self.datafolder}calibrations/{dev}.pickle.calib"):
            calibrationFile = open(f"{self.datafolder}calibrations/{dev}.pickle.calib",'rb')

        if calibrationFile is None:
            Logger.warn(f"no calibration file found for {dev}")
            return
        else:
            Logger.info(f"latest file found: {calibrationFile}")

        calibrationData = pickle.load(calibrationFile)
        calibrationFile.close()

        P = np.array([self.dfMag.x,self.dfMag.y,self.dfMag.z]).T

        center = calibrationData['center']
        radii = calibrationData['radii']
        rotation = calibrationData['rotation']

        Logger.info(f"calibration data: {calibrationData}")

        normedMax = max(radii)

        Logger.info(f"calibration data: {calibrationData}")

        normedMax = max(radii)

        Pcorr = P - center
        Pcorr = np.dot(Pcorr, rotation)
        Pcorr = ((Pcorr / radii) * normedMax * self.gaussTo_uTesla ) * normedMax * self.gaussTo_uTesla 

        # apply the calibration
        self.ds.mag = np.array([Pcorr[:,0],Pcorr[:,1],Pcorr[:,2]]).T
        
        magData = {
            't':self.dfMag.t,
            'x':self.ds.mag[:,0],
            'y':self.ds.mag[:,1],
            'z':self.ds.mag[:,2]
        }
        self.dfMag = pd.DataFrame(magData)
        self.updateDataSet()

    def getOffset(self,values,tMean):
        offset = np.mean(values[0:self.fs*tMean])
        return offset

    def calculateAndApplyGyroCalibration(self,dev,tMean = 3):  
        meanX = self.getOffset(self.dfGyr.x,tMean) 
        meanY = self.getOffset(self.dfGyr.y,tMean) 
        meanZ = self.getOffset(self.dfGyr.z,tMean) 
        self.dfGyr.x -= meanX
        self.dfGyr.y -= meanY
        self.dfGyr.z -= meanZ
        self.gyr = np.array([self.dfGyr.x,self.dfGyr.y,self.dfGyr.z]).T
        self.updateDataSet()
        Logger.info(f"applying gyro calibration: {meanX} {meanY} {meanZ}")
    
    def delete_processed_calibration_folders(self,directory=""):
        if directory == "":
            directory = f"{self.datafolder}/calibrations/"

        for root, dirs, files in os.walk(directory, topdown=False):
            for folder in dirs:
                folder_path = os.path.join(root, folder)
                if not os.listdir(folder_path):
                    print(f"Deleting empty folder: {folder_path}")
                    os.rmdir(folder_path)    
            

    def find_calibration_files(self,directory=""):
        if directory == "":
            directory = f"{self.datafolder}/calibrations/"

        # Recursively traverse directory tree and get all pickle files
        matches = []
        for root, dirnames, filenames in os.walk(directory):
            if not "archive" in root:
                for filename in fnmatch.filter(filenames, '*.pickle'):
                    matches.append(os.path.join(root, filename))
        # order matches based on modification time
        matches.sort(key=lambda x: os.path.getmtime(x))
        return matches

    def find_latest_pickle_file(self):
        # Recursively traverse directory tree and get all pickle files
        matches = []
        for root, dirnames, filenames in os.walk(self.datafolder):
            for filename in fnmatch.filter(filenames, '*.pickle'):
                matches.append(os.path.join(root, filename))

        # Get the latest pickle file based on modification time
        if matches:
            latest_file = max(matches, key=os.path.getmtime)
            return latest_file
        else:
            return None
    
    def find_all_data_files(self):
        # Recursively traverse directory tree and get all pickle files
        matches = []
        for root, dirnames, filenames in os.walk(self.datafolder):
            for filename in fnmatch.filter(filenames, '*.pickle'):
                matches.append(os.path.join(root, filename))

        # Get the latest pickle file based on modification time
        return matches     

    def processQuats(self):
        acc = self.acc * self.gToMs
        gyr = self.gyr * self.degreeToRad
        mag = self.mag
        self.quats['Tilt'] = Tilt(acc = self.acc, frequency=self.fs)
        self.quats['Integration'] = AngularRate(gyr = gyr, frequency=self.fs)
        self.quats['Madgwick'] = Madgwick(acc = acc, gyr = gyr, mag = mag, frequency=self.fs)
        self.quats['Mahony'] = Mahony(acc = acc, gyr = gyr, mag = mag, frequency=self.fs)
        self.quats['EKF'] = EKF(acc = acc, gyr = gyr, mag = mag, frequency=self.fs)

    def get_quaternions(self):
        return self.quats

    def get_dataset(self):
        dfAcc = self.dfAcc
        dfGyr = self.dfGyr 
        dfMag = self.dfMag 

        dfAcc.columns = ['accl_' + col if col != 't' else col for col in dfAcc.columns]
        dfGyr.columns = ['gyr_' + col if col != 't' else col for col in dfGyr.columns]
        dfMag.columns = ['mag_' + col if col != 't' else col for col in dfMag.columns]

        # Merging the dataframes
        df = pd.merge(dfAcc, dfGyr, on='t', how='outer')
        df = pd.merge(df, dfMag, on='t', how='outer')
        return df
        self.quats['EKF'] = EKF(acc = acc, gyr = gyr, mag = mag, frequency=self.fs)

    def get_quaternions(self):
        return self.quats

    def get_dataset(self):
        dfAcc = self.dfAcc
        dfGyr = self.dfGyr 
        dfMag = self.dfMag 

        dfAcc.columns = ['accl_' + col if col != 't' else col for col in dfAcc.columns]
        dfGyr.columns = ['gyr_' + col if col != 't' else col for col in dfGyr.columns]
        dfMag.columns = ['mag_' + col if col != 't' else col for col in dfMag.columns]

        # Merging the dataframes
        df = pd.merge(dfAcc, dfGyr, on='t', how='outer')
        df = pd.merge(df, dfMag, on='t', how='outer')
        return df
    
    def getDevices(self):
        return list(self.data.keys())

    def updateDataSet(self):
        self.ds = DataSet(acc = self.acc,gyr = self.gyr,mag = self.mag, bat = self.bat, temp = self.temp, quats = {},dfAcc = self.dfAcc,dfGyr = self.dfGyr,dfMag=self.dfMag, dfBat=self.dfBat,dfTemp=self.dfTemp, calibrationData=self.calibrationData)


    def calculateCalibrations(self,dev, directory=""):
        if directory == "":
            directory = f"{self.datafolder}/calibrations/"

        P = np.array([self.dfMag.x,self.dfMag.y,self.dfMag.z]).T
        ET = EllipsoidTool()
        (center, radii, rotation) = ET.getMinVolEllipse(P, .01)
        
        #Apply correction
        Pcorr = P - center
        Pcorr = np.dot(Pcorr, rotation)
        Pcorr = Pcorr / radii
        
        # save the calibration data in a picklefile under "calibrations", by the name of the device
        if not os.path.exists(directory):
            os.makedirs(directory)

        self.calibrationData = {'center':center,'radii':radii,'rotation':rotation}  
        Logger.info(f"calibration data: {self.calibrationData}")
        Logger.info(f"calibration data: {self.calibrationData}")
        dev = dev.replace(" ","_")
        dev = dev.replace(":","_")
        calibrationFile = open(f"{directory}/{dev}.pickle.calib",'wb')
        pickle.dump(self.calibrationData,calibrationFile)
        calibrationFile.close()    
        self.updateDataSet()


if __name__ == '__main__':
    parser = DumpFileParser()
    parser.find_and_parse_files()
    dp = DataProcessor("rawdata/")

    # You can use the following find the latest datafile, default is to loop through all fileS
    # You can also just give a fixed filename 
     
    #fileName = dp.find_latest_pickle_file()

   


    
    

# %%