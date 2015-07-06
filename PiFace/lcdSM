# StateMachine/State.py
# A State has an operation, and can be moved
# into the next State given an Input:
import sys
import re
import itertools
from threading import Barrier, Timer
import subprocess
from time import sleep
from random import randint
import pifacecad.core
import pifacecommon
from pifacecad.tools.scanf import *
from pifacecad.lcd import LCD_WIDTH
from configparser import ConfigParser
from statemachine import *

SETTLE_TIME = 0.200     # time in seconds for debounce time of switches
INACTIVE_TIME = 60      # Time in seconds to turn off display


class LCD_SM(StateMachine):
    def __init__(self, cad):
        # Initial state
        self.cad = cad
        self.parser = ConfigParser()
        self.configFile = '/home/pi/projects/PiFace/config.ini'
        self.parser.read(self.configFile)

        # Static variable initialization:
        LCD_SM.waiting = Waiting(cad, self)
        LCD_SM.menu = Menu(cad, self)
        LCD_SM.sections = Sections(cad, self)
        LCD_SM.options = Options(cad, self)
        LCD_SM.editing = Editing(cad, self)
        LCD_SM.scanning = Scanning(cad, self)
        
        StateMachine.__init__(self, LCD_SM.waiting)
        self.currentState = self.currentState.run()

        #Timer used to turn off display when inactive for
        self.t = Timer(INACTIVE_TIME, self.hibernate)

    def run(self, event):
        self.currentState = self.currentState[0].next(event.pin_num)

        #If a button has been pressed the program will be directed
        #here. Cancel the current timer and start a new timer
        if self.t.isAlive():
            self.t.cancel()
            self.t.join()
        if not self.t.isAlive():
            self.t = Timer(INACTIVE_TIME, self.hibernate)
            self.t.start()

        #The Waiting.run state does not require any arguments 
        if (len(self.currentState)>1):
            self.currentState[0].run(self.currentState[1])
        else:
            self.currentState[0].run()

    def hibernate(self):
        #If inactive put the display in waiting state
        self.currentState = LCD_SM.waiting.run()
        self.t.cancel()
    

if __name__ == "__main__":

    cad = pifacecad.PiFaceCAD()
    LCD_SM = LCD_SM(cad)

    # listener cannot deactivate itself so we have to wait until it has
    # finished using a barrier.
    global end_barrier
    end_barrier = Barrier(2)


    # wait for button presses
    switchlistener = pifacecad.SwitchEventListener(chip=cad)
    switchlistener.register(0, pifacecad.IODIR_ON, LCD_SM.run, SETTLE_TIME)
    switchlistener.register(1, pifacecad.IODIR_ON, LCD_SM.run, SETTLE_TIME)
    switchlistener.register(2, pifacecad.IODIR_ON, LCD_SM.run, SETTLE_TIME)
    switchlistener.register(3, pifacecad.IODIR_ON, LCD_SM.run, SETTLE_TIME)
    switchlistener.register(4, pifacecad.IODIR_ON, LCD_SM.run, SETTLE_TIME)
    switchlistener.register(5, pifacecad.IODIR_ON, LCD_SM.run, SETTLE_TIME)
    switchlistener.register(6, pifacecad.IODIR_ON, LCD_SM.run, SETTLE_TIME)
    switchlistener.register(7, pifacecad.IODIR_ON, LCD_SM.run, SETTLE_TIME)

    switchlistener.activate()
    end_barrier.wait()  # wait unitl exit

    #Deactivate LCD and exit program
    switchlistener.deactivate()


