# Copyright (c) 2019 Michael Schmidt
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import threading
import time
import datetime
import logging
import serial
from setup_logger import logger
import configparser

logger = logging.getLogger('CONTROLLER')
logger.setLevel(logging.INFO)

UPDATE_INVERVAL = 1            # frequency in seconds that controller should read data from serial connection
PORT = "/dev/ttyUSB0"
RATE = 19200
DEFAULT_ON_DELAY = 600
DEFAULT_TEMP = -999

CONFIGFILE = "controller.ini"

# Handles communication with Arduino over serial interface to read wired temperaturess and turn on/off heating and cooling devices
class Controller (threading.Thread):

    # Constructor using a configuration file for setting and updating properties to connect to the BrewFather app
    def __init__(self):
        threading.Thread.__init__(self)
    
        self.bStopThread = True             # flag used for stopping the background thread
        self.bStopRequest = False    

        self.onDelay = DEFAULT_ON_DELAY     # delay in seconds for when heating/cooling can turn ON after being turned OFF

        self.beerTemp = DEFAULT_TEMP                 # temperatures of beer that should be averaged to avoid jumps from reading to reading
        self.chamberTemp = DEFAULT_TEMP              # temperatures of refridgerator that should be average to avoid jumps from reading to reading
        self.internalTemp = DEFAULT_TEMP             # delta of internal temperature with safety limit (negative value means device has exceeded safety temperature) 

        self.beerTAdjust = 0.0
        self.chamberTAdjust = 0.0

        self.lastUpdateTime = datetime.datetime.now() - datetime.timedelta(seconds=UPDATE_INVERVAL) # last time the data was read

        self.bHeatOn = False;
        self.heatEndTime = datetime.datetime.now() - datetime.timedelta(seconds=self.onDelay) # last time heat turned off

        self.bCoolOn = False;
        self.coolEndTime = datetime.datetime.now() - datetime.timedelta(seconds=self.onDelay) # last time cool turned off

        self.ser = serial.Serial(PORT,RATE) # sets up serial communication
        self.ser.flushInput()               # flush any data that might be in channel

    # Starts the background thread
    def run(self):

        logger.info("Starting Controller")
        self.bStopThread = False
        
        while self.bStopThread != True:
            curTime = datetime.datetime.now()
            sTime = curTime.strftime("%d.%m.%Y %H:%M:%S")

            self._readConf()
             # request status from Arduino
            self._updateState()

            time.sleep(UPDATE_INVERVAL)

            # reads and processes all data from serial queue
            while self.ser.inWaiting() > 0:
                inputValue = self.ser.readline()
                str = inputValue.decode()
                str = str.strip()
                logger.debug("RESPONSE Raw: "+str)
                self._processControllerResponse(str)

            if self.bStopRequest:
                if not self.bCoolOn and not self.bHeatOn:
                    self.bStopThread = True
                else:
                    self.stopHeatingCooling()   


        logger.info("Controller Stopped")

    def __del__(self):
        logger.debug("Delete controller class")

    # handles data from Arduino over USB to RPi. Format is assumed to be "x:y" where x is the type of data and y is the content
    # C = Cooling
    #   + ON
    #   - OFF
    # H = Heating
    #   + ON
    #   - OFF
    # B = Beer
    #   # = temperature of beer
    # F = Fridge
    #   # = temperature of chamber
    # S = degrees to internal safety temperature (negative value indicates safe temperature exceeded)
    #   # = temperature of inside of controller to ensure device doesn't overheat
    def _processControllerResponse(self, str):
        try:
            curTime = datetime.datetime.now()
            sTime =  self.lastUpdateTime.strftime("%d.%m.%Y %H:%M:%S")

            lhs, rhs = str.split(":", 1)
            if lhs == "C":
                if rhs == "-":
                    logger.debug("("+sTime+"): Cooling is OFF")
                    if self.bCoolOn == True:
                        self.coolEndTime = curTime
                    self.bCoolOn = False
                elif rhs == "+":
                    logger.debug("("+sTime+"): Cooling is ON")
                    self.bCoolOn = True
            elif lhs == "H":
                if rhs == "-":
                    logger.debug("("+sTime+"): Heating is OFF")
                    if self.bHeatOn == True:
                        self.heatEndTime = curTime
                    self.bHeatOn = False
                elif rhs == "+":
                    logger.debug("("+sTime+"): Heating is ON")
                    self.bHeatOn = True
            elif lhs == "F":
                self.chamberTemp = float(rhs)
                logger.debug("("+sTime+"): Fridge temperature: {:5.3f}C".format(round(float(self.getChamberTemp()),1)))
                self.lastUpdateTime = curTime
            elif lhs == "B":
                self.beerTemp = float(rhs)
                logger.debug("("+sTime+"): Beer temperature: {:5.3f}C".format(round(float(self.getBeerTemp()),1)))
                self.lastUpdateTime = curTime
            elif lhs == "S":
                self.internalTemp = float(rhs)
                logger.debug("("+sTime+"): Delta to safety temperature: "+rhs+"C")
                self.lastUpdateTime = curTime

        except BaseException as e:
            logger.error("ERROR: %s\n" % str(e))


    # stops the background thread and requests heating and cooling to be stopped
    def stop(self):
        self.stopHeatingCooling()
        self.bStopRequest = True

    # request state
    def _updateState(self):
        sTime = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        logger.debug("("+sTime+"): Status request")
        self.ser.write(b'?\n')

    # requests cooling to start; this will turn off heating
    def startCooling(self):
        curTime = datetime.datetime.now()
        sTime = curTime.strftime("%d.%m.%Y %H:%M:%S")

        logger.debug("("+sTime+"): Cooling request")
            
        if curTime > self.coolEndTime + datetime.timedelta(seconds=self.onDelay):
            logger.debug("("+sTime+"): Cooling Turned ON")
            self.ser.write(b'C\n')
        else:
            logger.debug("("+sTime+"): Cooling delay has not expired")
            self.ser.write(b'O\n')


    # requests heating to start; this will turn off cooling
    def startHeating(self):
        curTime = datetime.datetime.now()
        sTime = curTime.strftime("%d.%m.%Y %H:%M:%S")
        
        logger.debug("("+sTime+"): Heating request")

        if curTime > self.heatEndTime + datetime.timedelta(seconds=self.onDelay):
            logger.debug("("+sTime+"): Heating Turned ON")
            self.ser.write(b'H\n')
        else:
            logger.debug("("+sTime+"): Heating delay has not expired")
            self.ser.write(b'O\n')

    # requests both heating and cooling to be stopped
    def stopHeatingCooling(self):
        sTime = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        logger.debug("("+sTime+"): Turned Off")
        self.ser.write(b'O\n')

    # returns time when data was updated
    def timeOfData(self):
        return self.lastUpdateTime

    # tells if data is valid
    def isDataValid(self):
        # if any of the expected values are still default then data is not valide
        if self.beerTemp == DEFAULT_TEMP or self.chamberTemp == DEFAULT_TEMP or self.internalTemp == DEFAULT_TEMP:
            return False
        # if data has not been updated then communication is broken with Arduino
        elif datetime.datetime.now() > self.lastUpdateTime + datetime.timedelta(seconds=UPDATE_INVERVAL*10):
            return False
        else:
            return True
        
    # returns beer temperature
    def getBeerTemp(self):
        if self.beerTemp == DEFAULT_TEMP:
            return None
        else:
            return round(float(self.beerTemp+self.beerTAdjust),1)

    # returns chamber temperature
    def getChamberTemp(self):    
        if self.chamberTemp == DEFAULT_TEMP:
            return None
        else:
            return round(float(self.chamberTemp+self.chamberTAdjust),1)

    # returns controller's internal temperature
    def getInternalTemp(self):
        if self.internalTemp == DEFAULT_TEMP:
            return None
        else:
            return round(float(self.internalTemp),1)

    def isHeating(self):
        return self.bHeatOn

    def isCooling(self):
        return self.bCoolOn


    # Read class parameters from configuration ini file.
    # Format:
    # [Controller]
    # OnDelay = 60
    # MessageLevel = INFO
    # BeerTempAdjust = 0.0
    # ChamberTempAdjust = 0.0

    def _readConf(self):

        try:
            if os.path.isfile(CONFIGFILE) == False:
                logger.error("Controller configuration file is not valid: "+CONFIGFILE)

            ini = configparser.ConfigParser()
            ini.read(CONFIGFILE)

            if 'Controller' in ini:
                logger.debug("Reading Controller config")
        
                config = ini['Controller']
                
                try:
                    if config["MessageLevel"] == "DEBUG":
                        logger.setLevel(logging.DEBUG)
                    elif config["MessageLevel"] == "WARNING":
                        logger.setLevel(logging.WARNING)
                    elif config["MessageLevel"] == "ERROR":
                        logger.setLevel(logging.ERROR)
                    elif config["MessageLevel"] == "INFO":
                        logger.setLevel(logging.INFO)
                    else:
                        logger.setLevel(logging.INFO)
                except KeyError:
                    logger.setLevel(logging.INFO)
                
                try:
                    if config["BeerTempAdjust"] != "":
                        self.beerTAdjust = float(config.get("BeerTempAdjust"))
                    else:
                        raise Exception
                except:
                    self.beerTAdjust = 0.0
                    logger.warning("Invalid BeerTempAdjust in configuration; using default: "+str(self.beerTAdjust))

                try:
                    if config["ChamberTempAdjust"] != "":
                        self.chamberTAdjust = float(config.get("ChamberTempAdjust"))
                    else:
                        raise Exception
                except:
                    self.chamberTAdjust = 0.0
                    logger.warning("Invalid BeerTempAdjust in configuration; using default: "+str(self.chamberTAdjust))

                try:
                    if config["OnDelay"] != "" and int(config["OnDelay"]) >= 0:
                        self.onDelay = int(config.get("OnDelay"))*60
                    else:
                        raise Exception
                except:
                    self.onDelay = DEFAULT_ON_DELAY
                    logger.warning("Invalid OnDelay in configuration; using default: "+str(self.onDelay))

        except:
            logger.warning("Problem read from configuration file: "+CONFIGFILE)
       
        logger.debug("Controller config updated")
