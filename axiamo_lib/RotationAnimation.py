from vpython import *
from time import *
import numpy as np
import pytransform3d.rotations as p3r
from axiamo_lib.BaseLogger import Logger

def toVec(list):
        return vector(list[0],list[1],list[2])
    
class RotationAnimation:
    def __init__(self,dist = 1.2,axis='x'):
        self.xa = [1,0,0]
        self.ya = [0,1,0]
        self.za = [0,0,1]
        self.vxa = toVec(self.xa)
        self.vya = toVec(self.ya)
        self.vza = toVec(self.za)
        self.pointerX = [dist, 0, 0]
        self.pointerY = [0, dist, 0]
        self.pointerZ = [0, 0, dist]        
        self.axis = axis        
        self.dist = dist
        self.pZero = vector(0,0,0)
        self.quats = []
        self.fs = 200
    
    def setQuats(self,quats):
        self.quats = quats

    def sliderCallback(self,s):
        try:
            numberOfQuats = len(self.quats)-1
            index = int(s.value*numberOfQuats)
            Logger.info(f"Quat slider callback, number of quats/index: {numberOfQuats}/{index}")
            currentTime = index/self.fs
            self.updateRotation(self.quats[index])
            Logger.info(f"time: {currentTime}")
        except Exception as e:
            Logger.error(f"Error in sliderCallback: {e}")


    def initGraphics(self):
        self.xarrow=arrow(lenght=2, shaftwidth=.1, color=color.red,axis=self.vxa)
        self.yarrow=arrow(lenght=2, shaftwidth=.1, color=color.green,axis=self.vya)
        self.zarrow=arrow(lenght=2, shaftwidth=.1, color=color.blue,axis=self.vza)
        #self.timeText = text(text='12 s',     align='lower_left', height='.2', color=color.green)

        self.updateRotation(p3r.quaternion_from_angle(1,0))
        slider( bind=self.sliderCallback )
        scene.append_to_caption('\n\n')
   
    def updateRotation(self, qR):
        # xArrows rotated
        xaR = p3r.q_prod_vector(qR, self.xa)            
        yaR = p3r.q_prod_vector(qR, self.ya)
        zaR = p3r.q_prod_vector(qR, self.za) 

        # vectors used to update graphic objects
        self.vxa = toVec(xaR)
        self.vya = toVec(yaR)
        self.vza = toVec(zaR)

        self.xarrow.axis = self.vxa
        self.yarrow.axis = self.vya
        self.zarrow.axis = self.vza

if __name__=='__main__':
    ra = RotationAnimation()
    ra.initGraphics()
    angle = 0
    while True:
        rate(100)
        q = p3r.quaternion_from_angle(1,angle)
        ra.updateRotation(q)
        angle +=.01
        ra.updateAnimation()