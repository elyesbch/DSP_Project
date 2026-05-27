import time
import csv
import logging
import pickle

Logger = logging.getLogger()
Logger.setLevel(logging.INFO)


class FileDumper:
    startTime = 0
    meta_dict = {}
    dataToWrite = []
    gattDataToWrite = {}
    freeLapLaps = []
    freeLapFx = []
    tags = []
    nX22Data = 0
    nGattData = 0
    nFreeLapData = 0
    # nLapsData = 0
    fileIsOpen = False

    minX22Data = 100
    minGattData = 20
    minFreeLapData = 10

    def __init__(self):
        self.username = "anonymous"
        self.activity = "none"
        self.motionname = "device"

    def setUserName(self, username):
        self.username = username
        if username:
            self.meta_dict["username"] = self.username
        else:
            self.meta_dict.pop("username", None)

        Logger.info(f"Filedump: Set username to: {username}")

    def setActivity(self, activity):
        self.activity = activity
        if activity:
            self.meta_dict["activity"] = self.activity
        else:
            self.meta_dict.pop("activity", None)

        Logger.info(f"Filedump: Set activity to: {activity}")

    def setMotionName(self, motionname):
        self.motionname = motionname
        if motionname:
            self.meta_dict["device_name"] = self.motionname
        else:
            self.meta_dict.pop("device_name", None)

        Logger.info(f"Filedump: Set motionName to: {motionname}")

    def setRecordMeta(self, metaDict):
        for key in metaDict:
            self.meta_dict[key] = metaDict[key]
        Logger.info(f"Filedump: Set meta_dict to: {str(metaDict)}")

    def openFiles(self, path):
        self.nX22Data = 0
        self.nGattData = 0
        self.nLapData = 0
        self.nLapsData = 0

        self.startTime = round(time.time())
        self.dataToWrite = []
        self.gattDataToWrite = {}
        self.gattDataToWrite["tags"] = self.tags
        self.tags = []
        self.freeLapLaps = []
        self.freeLapFx = []
        motionname = self.motionname.replace(":", "").replace(" ", "_")
        self.baseFileName = (
            path
            + "/"
            + self.username
            + "_"
            + str(self.startTime)
            + "_"
            + motionname
            + "cycling_data"
        )
        self.fileIsOpen = True
        self.writex22Data()

    def writex22Data(self):
        if not self.fileIsOpen:
            return
        with open(self.baseFileName + ".csv", "w") as dumpFileMotion:
            self.csvwriter = csv.writer(dumpFileMotion, delimiter=",")
            headerRow = ["iterator", "type", "x", "y", "z"] + [
                key for key in self.meta_dict
            ]
            self.csvwriter.writerow(headerRow)
            if dumpFileMotion:
                firstRow = [
                    val for val in self.meta_dict.values()
                ]  # pyright: ignore[reportGeneralTypeIss ues]
                if len(self.dataToWrite) > 0:
                    firstRow = self.dataToWrite.pop(0) + firstRow
                else:
                    firstRow = [""] * 5 + firstRow
                self.csvwriter.writerow(firstRow)
                if len(self.dataToWrite) > 0:
                    self.csvwriter.writerows(self.dataToWrite)
                dumpFileMotion.close()

    def writeGattData(self):
        if not self.fileIsOpen:
            return
        if len(self.gattDataToWrite.keys()) > 0:
            pickleFileName = self.baseFileName + ".pic"
            with open(pickleFileName, "wb") as pickleFile:
                pickle.dump(self.gattDataToWrite, pickleFile)
                # Logger.info(f"Filedump: Gattdata {self.gattDataToWrite}")

    def writeFreeLapData(self):
        if not self.fileIsOpen:
            return
        if len(self.freeLapLaps) > 0:
            freeLapLapFileName = self.baseFileName + "_freelap_lap" + ".csv"
            with open(freeLapLapFileName, "w") as dumpFileFreeLapLap:
                self.csvwriter = csv.writer(dumpFileFreeLapLap, delimiter=",")
                headerRow = ["walltime", "device", "laps"]
                self.csvwriter.writerow(headerRow)
                self.csvwriter.writerows(self.freeLapLaps)
                dumpFileFreeLapLap.close()

        # Logger.info(f"Freelap FX info {len(self.freeLapFx)}")
        if len(self.freeLapFx) > 0:
            freeLapFxFileName = self.baseFileName + "_freelap_fx" + ".csv"
            with open(freeLapFxFileName, "w") as dumpFileFreeLapFx:
                self.csvwriter = csv.writer(dumpFileFreeLapFx, delimiter=",")
                headerRow = [
                    "walltime",
                    "device",
                    "offset",
                    "fromlap",
                    "totallap",
                    "batteryLevel",
                ]
                self.csvwriter.writerow(headerRow)
                self.csvwriter.writerows(self.freeLapFx)
                dumpFileFreeLapFx.close()

    def closeFiles(self):
        Logger.info("Filedumper writes files")
        self.writex22Data()
        self.writeGattData()
        self.writeFreeLapData()
        self.fileIsOpen = False

    def appendData(self, data):
        self.dataToWrite += data
        self.nX22Data += len(data)
        if self.nX22Data > self.minX22Data:
            self.writex22Data()
            self.nX22Data = 0

    def appendFreeLapLaps(self, device, laps, timestamp):
        print(f"dev: {device}, laps: {laps}")
        now = timestamp
        self.freeLapLaps.append([now, device] + list(laps))
        self.nFreeLapData += len(laps)
        if self.nFreeLapData > self.minFreeLapData:
            self.writeFreeLapData()
            self.nFreeLapData = 0

    def appendFreeLapFx(
        self, device, offset, fromlap, totallap, batteryLevel, timestamp
    ):
        now = timestamp
        self.freeLapFx.append([now, device, offset, fromlap, totallap, batteryLevel])
        self.nFreeLapData += 1
        if self.nFreeLapData > self.minFreeLapData:
            self.writeFreeLapData()
            self.nFreeLapData = 0

    def appendGattData(self, gattDict):
        for key in gattDict:
            if isinstance(gattDict[key], dict):
                if key not in self.gattDataToWrite:
                    self.gattDataToWrite[key] = {}
                for gattKey in gattDict[key]:
                    if gattKey == "fields":
                        if gattKey not in self.gattDataToWrite[key]:
                            self.gattDataToWrite[key]["fields"] = gattDict[key][
                                "fields"
                            ]
                        continue
                    elif gattKey not in self.gattDataToWrite[key]:
                        self.gattDataToWrite[key][gattKey] = []
                    elif len(self.gattDataToWrite[key][gattKey]) > 0:
                        if (
                            self.gattDataToWrite[key][gattKey][-1]
                            == gattDict[key][gattKey][-1]
                        ):
                            continue
                    # Logger.info(f"{self.gattDataToWrite[key][gattKey]} {gattDict } {key} {gattKey}")
                    self.gattDataToWrite[key][gattKey] += gattDict[key][gattKey]
                    self.nGattData += len(gattDict[key][gattKey])
            else:
                if key not in self.gattDataToWrite:
                    self.gattDataToWrite[key] = []
                else:
                    if self.gattDataToWrite[key][-1] == gattDict[key][-1]:
                        continue
                self.gattDataToWrite[key] += gattDict[key]
                self.nGattData += len(gattDict[key])

        if self.nGattData > self.minGattData:
            self.writeGattData()
            self.nGattData = 0

    def appendGPSData(self, gpsDict):
        if "gps" not in self.gattDataToWrite:
            self.gattDataToWrite["gps"] = {}
        for gpsKey in gpsDict["gps"]:
            if gpsKey not in self.gattDataToWrite["gps"]:
                self.gattDataToWrite["gps"][gpsKey] = []
            self.gattDataToWrite["gps"][gpsKey] += gpsDict["gps"][gpsKey]
            self.nGattData += len(gpsDict["gps"][gpsKey])
        if self.nGattData > self.minGattData:
            self.writeGattData()
            self.nGattData = 0

    def setTag(self, tag):
        if tag not in self.tags:
            self.tags.append(tag)
            Logger.info(f"setTag append: {self.gattDataToWrite}")

    # def unsetTag(self, tag):
    #     if "tags" not in self.gattDataToWrite:
    #         return
    #     if tag in self.gattDataToWrite["tags"]:
    #         self.gattDataToWrite["tags"].remove(tag)
