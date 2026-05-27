import numpy as np
from axiamo_lib.BaseLogger import Logger
class DataSet(object):
    def __init__(self , acc,gyr,mag,bat,temp,quats,dfAcc,dfGyr,dfMag,dfBat,dfTemp,calibrationData):
        self.acc = acc
        self.gyr = gyr
        self.mag = mag
        self.bat = bat
        self.temp = temp
        self.quats = quats
        self.dfAcc = dfAcc
        self.dfGyr = dfGyr
        self.dfMag = dfMag
        self.dfBat = dfBat
        self.dfTemp = dfTemp
        self.calibrationData = calibrationData
    
    def printStats(self):
        #get the difference in time between each sample
        dt = np.round(np.diff(self.dfAcc.t),4)
        #count the occurences of each time difference
        unique, counts = np.unique(dt, return_counts=True)
        Logger.info(f"Unique time differences: {unique} , counts: {counts}")
