import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from axiamo_lib.DataSet import DataSet
from axiamo_lib.RotationAnimation import RotationAnimation
from axiamo_lib.BaseLogger import Logger
import numpy as np
from scipy.spatial.transform import Rotation as R
from ahrs.common.orientation import q2R
from plotly.subplots import make_subplots
import plotly.graph_objs as go

class Visualizer:
    def __init__(self,use3Dviewer=False):
        self.ds = None
        self.animationRate = 200
        # if use3Dviewer:
        #     from vpython import *
        #     self.init3DView()

    def setDataSet(self,ds):
        self.ds = ds

    def visualizeRawData(self):
        ds = self.ds
        #plot the raw data to work with
        figAcc = px.line(ds.dfAcc,x='t',y=ds.dfAcc.columns,title="Acceleration")
        figGyr = px.line(ds.dfGyr,x='t',y=ds.dfGyr.columns,title="Gyroscope")
        figMag2 = px.line(ds.dfMag,x='t',y=ds.dfMag.columns,title="Magnetometer")
        figMag = px.scatter_3d(ds.dfMag, x=ds.dfMag.x, y=ds.dfMag.y, z=ds.dfMag.z,opacity=0.1,title="Magnetometer")

        figAcc.show()
        figGyr.show()
        figMag.show()
        figMag2.show()


    def visualizeTime(self,dp):
        ds = dp.ds
        figTime = px.scatter(y=ds.dfAcc.t)
        figTime.show()

    def visualizeRawDataSubPlot(self,dp,title):
        ds = dp.ds  # Assuming 'ds' is a property of the class instance with the required data

        # Function to transform local accelerations to global frame using quaternions
        def transform_acc_with_quat(acc, quat):
            # Convert quaternion to rotation matrix using ahrs
            rotation_matrix = q2R(quat)
            # Transform the acceleration
            global_acc = np.dot(rotation_matrix, acc)
            return global_acc

        # Extract acceleration data and quaternions
        acc_data = ds.dfAcc[['x', 'y', 'z']].values  # Assuming dfAcc has columns x, y, z for acceleration
        rows = 2
        showGlobalAcc = False
        showBattery = False
        showMag = False

        if 'Madgwick' in dp.quats:
            showGlobalAcc = True
            rows += 1

        if showBattery:
            rows += 1

        if showGlobalAcc:
            quats = dp.quats['Madgwick'].Q  # Array of quaternions
            # Calculate global accelerations
            global_accs = np.array([transform_acc_with_quat(acc, quat) for acc, quat in zip(acc_data, quats)])
        
        if showMag:
            rows += 1

        # Create subplots
        fig = make_subplots(rows=rows, cols=1, shared_xaxes=True)

        # Update y-axis titles
        fig.update_yaxes(title_text="Acceleration [g]", row=1, col=1)
        fig.update_yaxes(title_text="Gyroscope [deg/s]", row=2, col=1)
        
        if showMag:
            fig.update_yaxes(title_text="Magnetometer [uT]", row=3, col=1)


        # Add traces for original and global acceleration
        row = 1
        fig.add_trace(go.Scatter(x=ds.dfAcc.t, y=ds.dfAcc.x, name="accX", line=dict(color='red')), row=row, col=1)
        fig.add_trace(go.Scatter(x=ds.dfAcc.t, y=ds.dfAcc.y, name="accY", line=dict(color='green')), row=row, col=1)
        fig.add_trace(go.Scatter(x=ds.dfAcc.t, y=ds.dfAcc.z, name="accZ", line=dict(color='blue')), row=row, col=1)
        row += 1
        fig.add_trace(go.Scatter(x=ds.dfGyr.t, y=ds.dfGyr.x, name="gyrX", line=dict(color='red')), row=row, col=1)
        fig.add_trace(go.Scatter(x=ds.dfGyr.t, y=ds.dfGyr.y, name="gyrY", line=dict(color='green')), row=row, col=1)
        fig.add_trace(go.Scatter(x=ds.dfGyr.t, y=ds.dfGyr.z, name="gyrZ", line=dict(color='blue')), row=row, col=1)
        row += 1

        if showMag:
            fig.add_trace(go.Scatter(x=ds.dfMag.t, y=ds.dfMag.x, name="magX", line=dict(color='red')), row=row, col=1)
            fig.add_trace(go.Scatter(x=ds.dfMag.t, y=ds.dfMag.y, name="magY", line=dict(color='green')), row=row, col=1)
            fig.add_trace(go.Scatter(x=ds.dfMag.t, y=ds.dfMag.z, name="magZ", line=dict(color='blue')), row=row, col=1)

        if showGlobalAcc:
            # Add traces for global acceleration
            row += 1
            fig.add_trace(go.Scatter(x=ds.dfAcc.t, y=global_accs[:, 0], name="globalAccX", line=dict(color='red')), row=row, col=1)
            fig.add_trace(go.Scatter(x=ds.dfAcc.t, y=global_accs[:, 1], name="globalAccY", line=dict(color='green')), row=row, col=1)
            fig.add_trace(go.Scatter(x=ds.dfAcc.t, y=global_accs[:, 2], name="globalAccZ", line=dict(color='blue')), row=row, col=1)
            fig.update_yaxes(title_text="Global Acceleration [g]", row=4, col=1)
            
        if showBattery:
            # Add traces for battery
            row += 1
            fig.add_trace(go.Scatter(x=ds.dfBat.t, y=ds.dfBat.mVolt/100, name="mVolt x10"), row=row, col=1)
            fig.add_trace(go.Scatter(x=ds.dfBat.t, y=ds.dfBat.mA, name="mAmps"), row=row, col=1)
            fig.add_trace(go.Scatter(x=ds.dfTemp.t, y=ds.dfTemp.temp, name="temp"), row=row, col=1)            
            fig.update_yaxes(title_text="Battery / Temperature", row=row, col=1)
            #fig.add_trace(go.Scatter(x=ds.dfBat.t, y=ds.dfBat.perc, name="%"), row=row, col=1)

        fig.update_layout(title_text=title)
        # Show the plot
        fig.show()

    def init3DView(self):
        self.ra = RotationAnimation(axis='z')
        self.ra.initGraphics()

    def update3DView(self,q):
        self.ra.updateRotation(q)
        rate(self.animationRate)

    def setQuats(self,quats,selectedQuats):
        self.quats = quats
        self.selectedQuats = selectedQuats
        self.ra.setQuats(self.quats[self.selectedQuats].Q)

    def animateQuats(self):
        for q in self.quats[self.selectedQuats].Q:
            #Logger.info(f"current quat q: {q}")
            self.update3DView(q)

    def visualizeCalibration(self):
        ds = self.ds
        figMagCalib = px.scatter_3d(x=ds.dfMag.x, y=ds.dfMag.y, z=ds.dfMag.z,opacity=0.1,title="Magnetometer Calibrated")
        figMagCalib.show()

        pass
        #         figMagCalib = px.scatter_3d(dfMag, x=Pcorr[:,0], y=Pcorr[:,1], z=Pcorr[:,2],opacity=0.1,title="Magnetometer Calibrated")
        # figMag.show()
        # figMag2.show()
        # figMagCalib.show()
