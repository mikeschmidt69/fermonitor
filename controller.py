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

logger = logging.getLogger('CONTROLLER')
logger.setLevel(logging.INFO)

NUMBER_TEMP_AVERAGE = 20        # number of temperature readings that should be averaged to avoid jumps in temperature from reading to reading
UPDATE_INVERVAL = 10            # frequency that controller should read data from serial connection
PORT = "/dev/ttyUSB0"
RATE = 9600

# Handles communication with Arduino over serial interface to read wired temperaturess and turn on/off heating and cooling devices
class Controller (threading.Thread):

    # Constructor using a configuration file for setting and updating properties to connect to the BrewFather app
    def __init__(self):
        threading.Thread.__init__(self)
    
        self.stopThread = True              # flag used for stopping the background thread
        self.onDelay = -1                   # delay for when heating/cooling can turn ON after being turned OFF
        self.requestedDelay = -1            # new delay for turning on/off heating and cooling that should be requested from Arduino
        self.beerTemp = 0.0                 # temperatures of beer that should be averaged to avoid jumps from reading to reading
        self.fridgeTemp = 0.0               # temperatures of refridgerator that should be average to avoid jumps from reading to reading
        self.internalTemp = 0.0             # internal temperature of control box
        self.adjustBeerT = 0.0              # adjustment to beer temperature to correct for sensor offset
        self.adjustFridgeT = 0.0            # adjustement to refridgerator temperature to correct for sensor offset
        

        self.lastUpdateTime = datetime.datetime.now() - datetime.timedelta(seconds=UPDATE_INVERVAL) # last time the data was read

        self.ser = serial.Serial(PORT,RATE) # sets up serial communication
        self.ser.flushInput()               # flush any data that might be in channel

    # Starts the background thread
    def run(self):
        logger.info("Starting Controller")
        self.stopThread = False
        
        while self.stopThread != True:
            # reads and processes all data from serial queue
            while self.ser.inWaiting() > 0:
                inputValue = self.ser.readline()
                str = inputValue.decode()
                str = str.strip()
                logger.debug("RESPONSE Raw: "+str)
                self._processControllerResponse(str)

            self._handleDelay()

            time.sleep(UPDATE_INVERVAL)

        logger.info("Controller Stopped")

    # handles data from Arduino over USB to RPi. Format is assumed to be "x:y" where x is the type of data and y is the content
    # D = ON delay between turning off and back on a conntected heating or cooling device; data is in milliseconds
    # C = Cooling
    #   - = turned off
    #   + = turned on
    #   # = number of milliseconds cooling has been ON
    # c = cooling
    #   - = requested to be turned off but action hasn't happened yet
    #   + = requested to be turned on but action hasn't happened yet
    #   # = number of milliseconds before device will be turned on; dependes on delay (D)
    # H = Heating
    #   - = turned off
    #   + = turned on
    #   # = number of milliseconds heating has been ON
    # h = heating
    #   - = requested to be turned off but action hasn't happened yet
    #   + = requested to be turned on but action hasn't happened yet
    #   # = number of milliseconds before device will be turned on; dependes on delay (D)
    # O = heating and cooling are OFF
    # B = Beer
    #   # = temperature of beer
    # F = Fridge
    #   # = temperature of fridge
    # I = Internal
    #   # = temperature of inside of controller to ensure device doesn't overheat
    def _processControllerResponse(self, str):
        try:
            sTime = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")

            lhs, rhs = str.split(":", 1)
            if lhs == "D":
                logger.debug("RESPONSE ("+sTime+"): On delay: "+rhs)
                self.onDelay = int(rhs)
            elif lhs == "c":
                if rhs == "-":
                    logger.debug("RESPONSE ("+sTime+"): Cooling requested to be turned OFF")
                elif rhs == "+":
                    logger.debug("RESPONSE ("+sTime+"): Cooling requested to be turned ON")
                else:
                    logger.debug("RESPONSE ("+sTime+"): Cooling will be turned on in: "+rhs+"m")
            elif lhs == "C":
                if rhs == "-":
                    logger.info("RESPONSE ("+sTime+"): Cooling turned OFF")
                elif rhs == "+":
                    logger.info("RESPONSE ("+sTime+"): Cooling turned ON")
                else:
                    logger.debug("RESPONSE ("+sTime+"): Cooling on for "+rhs+"m")
            elif lhs == "h":
                if rhs == "-":
                    logger.debug("RESPONSE ("+sTime+"): Heating requested to be turned OFF")
                elif rhs == "+":
                    logger.debug("RESPONSE ("+sTime+"): Heating requested to be turned ON")
                else:
                    logger.debug("RESPONSE ("+sTime+"): Heating will be turned on in: "+rhs+"m")
            elif lhs == "H":
                if rhs == "-":
                    logger.info("RESPONSE ("+sTime+"): Heating turned OFF")
                elif rhs == "+":
                    logger.info("RESPONSE ("+sTime+"): Heating turned ON")
                else:
                    logger.debug("RESPONSE ("+sTime+"): Cooling on for "+rhs+"m")
            elif lhs == "O":
                logger.debug("RESPONSE ("+sTime+"): Heating/Cooling are OFF for "+rhs+"m")
            elif lhs == "F":
                self.fridgeTemp = float(rhs) + self.adjustFridgeT
                self.lastUpdateTime = datetime.datetime.now()
                logger.debug("RESPONSE ("+sTime+"): Fridge temperature: "+rhs+"C")
            elif lhs == "B":
                self.beerTemp = float(rhs) + self.adjustBeerT
                self.lastUpdateTime = datetime.datetime.now()
                logger.debug("RESPONSE ("+sTime+"): Beer temperature: "+rhs+"C")
            elif lhs == "I":
                self.internalTemp = float(rhs)
                self.lastUpdateTime = datetime.datetime.now()
                logger.debug("RESPONSE ("+sTime+"): Internal temperature: "+rhs+"C")

        except BaseException as e:
            logger.error("ERROR: %s\n" % str(e))


    # send request to Arduino "=" to report current on delay
    def _requestCurrentDelay(self):
        sTime = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        logger.debug("REQUEST ("+sTime+"): current delay")
        self.ser.write(b'=\n')

    def _handleDelay(self):
        sTime = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")

        # check if delay period has been requested (!=-1) and if the current delay period has been received (!= -1)
        if self.requestedDelay != -1 and self.onDelay != -1:

            # if requested delay is longer than current, calculate # of steps delay should be increased and send request over serial
            if self.requestedDelay > self.onDelay:
                steps = round (self.requestedDelay-self.onDelay)
                for x in range(steps):
                    logger.debug("REQUEST ("+sTime+"): longer delay")
                    self.ser.write(b'+\n')
            # if requested delay is shorter than current, calculate # of steps delay should be decreased and send request over serial
            if self.requestedDelay < self.onDelay:
                steps = round (self.onDelay-self.requestedDelay)
                for x in range(steps):
                    logger.debug("REQUEST ("+sTime+"): shorter delay")
                    self.ser.write(b'-\n')
            # mark that requested delay has been handled
            self.requestedDelay = -1

                # stops the background thread and requests heating and cooling to be stopped
    def stop(self):
        self.stopHeatingCooling()
        self.stopThread = True

    # requests cooling to start; this will turn off heating
    def startCooling(self):
        sTime = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        logger.debug("REQUEST ("+sTime+"): cooling")
        self.ser.write(b'c\n')

    # requests heating to start; this will turn off cooling
    def startHeating(self):
        sTime = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        logger.debug("REQUEST ("+sTime+"): heating")
        self.ser.write(b'h\n')

    # requests both heating and cooling to be stopped
    def stopHeatingCooling(self):
        sTime = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        logger.debug("REQUEST ("+sTime+"): off")
        self.ser.write(b'o\n')

    # configure the delay between turning off/on of the heating and cooling devices connected to controiller
    def setConfig(self, _delay, _adjustBeerT, _adjustFridgeT):
        self.requestedDelay = _delay
        self.adjustBeerT = _adjustBeerT
        self.adjustFridgeT = _adjustFridgeT

    # returns time when data was updated
    def timeOfData(self):
        return self.lastUpdateTime

    # returns beer temperature
    def getBeerTemp(self):
        return round(float(self.beerTemp),1)

    # returns fridge temperature
    def getFridgeTemp(self):    
        return round(float(self.fridgeTemp),1)

    # returns controller's internal temperature
    def getInternalTemp(self):
        return round(float(self.internalTemp),1)

    # set logging level
    def setLogLevel(self, level):
        if level == logging.DEBUG:
            logger.setLevel(logging.DEBUG)
        elif level == logging.WARNING:
            logger.setLevel(logging.WARNING)
        elif level == logging.ERROR:
            logger.setLevel(logging.ERROR)
        elif level == logging.INFO:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.INFO)