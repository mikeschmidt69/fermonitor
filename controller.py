#
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

ON_DELAY_STEP = 60000 # 1 minute in milliseconds

import os
import threading
import time
import datetime
import logging
import serial
from setup_logger import logger

logger = logging.getLogger('CONTROLLER')
logger.setLevel(logging.INFO)

NUMBER_TEMP_AVERAGE = 20
UPDATE_INVERVAL = 10 # update interval in seconds
PORT = "/dev/ttyUSB0"
RATE = 9600

class Controller (threading.Thread):

    # Constructor using a configuration file for setting and updating properties to connect to the BrewFather app
    def __init__(self):
        threading.Thread.__init__(self)
    
        self.stopThread = True              # flag used for stopping the background thread
        self.onDelay = 0                    # delay for when heating/cooling can turn ON after being turned OFF
        self.requestedDelay = -1
        self.beerTemp = []
        self.fridgeTemp = []
        self.internalTemp = 0.0
        self.adjustBeerT = 0.0
        self.adjustFridgeT = 0.0
        

        self.lastUpdateTime = datetime.datetime.now() - datetime.timedelta(seconds=UPDATE_INVERVAL) # last time the sensor was read

        self.ser = serial.Serial(PORT,RATE)
        self.ser.flushInput()

    # Starts the background thread
    def run(self):
        logger.info("Starting Controller")
        self.stopThread = False
        
        while self.stopThread != True:
            self._requestCurrentDelay()

            while self.ser.inWaiting() > 0:
                inputValue = self.ser.readline()
                str = inputValue.decode()
                str = str.strip()
                logger.debug("RESPONSE Raw: "+str)
                self._processControllerResponse(str)

            if self.requestedDelay != -1:
                if self.requestedDelay > self.onDelay:
                    steps = round ((self.requestedDelay-self.onDelay)/ON_DELAY_STEP)
                    for x in range(steps):
                        self._requestLongerDelay()
                if self.requestedDelay < self.onDelay:
                    steps = round ((self.onDelay-self.requestedDelay)/ON_DELAY_STEP)
                    for x in range(steps):
                        self._requestShorterDelay()
                self.requestedDelay = -1

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
                    logger.debug("RESPONSE ("+sTime+"): Cooling will be turned on in: "+rhs+"ms")
            elif lhs == "C":
                if rhs == "-":
                    logger.info("RESPONSE ("+sTime+"): Cooling turned OFF")
                elif rhs == "+":
                    logger.info("RESPONSE ("+sTime+"): Cooling turned ON")
                else:
                    logger.debug("RESPONSE ("+sTime+"): Cooling on for "+rhs+"ms")
            elif lhs == "h":
                if rhs == "-":
                    logger.debug("RESPONSE ("+sTime+"): Heating requested to be turned OFF")
                elif rhs == "+":
                    logger.debug("RESPONSE ("+sTime+"): Heating requested to be turned ON")
                else:
                    logger.debug("RESPONSE ("+sTime+"): Heating will be turned on in: "+rhs+"ms")
            elif lhs == "H":
                if rhs == "-":
                    logger.info("RESPONSE ("+sTime+"): Heating turned OFF")
                elif rhs == "+":
                    logger.info("RESPONSE ("+sTime+"): Heating turned ON")
                else:
                    logger.debug("RESPONSE ("+sTime+"): Cooling on for "+rhs+"ms")
            elif lhs == "O":
                logger.debug("RESPONSE ("+sTime+"): Heating/Cooling are OFF")
            elif lhs == "F":
                _fridgeTemp = float(rhs) + self.adjustFridgeT
                self.fridgeTemp = self._addTemp(NUMBER_TEMP_AVERAGE, self.fridgeTemp, _fridgeTemp)
                self.lastUpdateTime = datetime.datetime.now()
                logger.debug("RESPONSE ("+sTime+"): Fridge temperature: "+rhs+"C")
            elif lhs == "B":
                _beerTemp = float(rhs) + self.adjustBeerT
                self.beerTemp = self._addTemp(NUMBER_TEMP_AVERAGE, self.beerTemp, _beerTemp)
                self.lastUpdateTime = datetime.datetime.now()
                logger.debug("RESPONSE ("+sTime+"): Beer temperature: "+rhs+"C")
            elif lhs == "I":
                self.internalTemp = float(rhs)
                self.lastUpdateTime = datetime.datetime.now()
                logger.debug("RESPONSE ("+sTime+"): Internal temperature: "+rhs+"C")
        except BaseException as e:
            logger.error( "ERROR: %s\n" % str(e) )

    # send request to Arduino "=" to report current on delay
    def _requestCurrentDelay(self):
        sTime = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        logger.debug("REQUEST ("+sTime+"): current delay")
        self.ser.write(b'=\n')

    # send request to Arduino "+" to increase the on delay on step
    def _requestLongerDelay(self):
        sTime = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        logger.debug("REQUEST ("+sTime+"): longer delay")
        self.ser.write(b'+\n')

    # send request to Arduino "-" to decrease the on delay on step
    def _requestShorterDelay(self):
        sTime = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        logger.debug("REQUEST ("+sTime+"): shorter delay")
        self.ser.write(b'-\n')

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
        self.requestedDelay = _delay * ON_DELAY_STEP
        self.adjustBeerT = _adjustBeerT
        self.adjustFridgeT = _adjustFridgeT

    # returns time when data was updated
    def timeOfData(self):
        return self.lastUpdateTime

    # returns beer temperature
    def getBeerTemp(self):
        _tempSum = 0.0
        
        for tmp in self.beerTemp:
            _tempSum = _tempSum + tmp

        _temp = 0.0

        if len(self.beerTemp) > 0:
            _temp = _tempSum/len(self.beerTemp)
        else:
            _temp = _tempSum
        return round(float(_temp),1)

    # returns fridge temperature
    def getFridgeTemp(self):
        _tempSum = 0.0
        
        for tmp in self.fridgeTemp:
            _tempSum = _tempSum + tmp

        _temp = 0.0

        if len(self.fridgeTemp) > 0:
            _temp = _tempSum/len(self.fridgeTemp)
        else:
            _temp = _tempSum
    
        return round(float(_temp),1)

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

    def _addTemp(self, _size, _array, _temp):
        while len(_array) > _size - 1:
            _array.pop(0)
        _array.append(_temp)
        return _array
        
