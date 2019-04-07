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

import threading
import datetime
import time
import logging
import controller
import tilt
from setup_logger import logger

logger = logging.getLogger('CHAMBER')
logger.setLevel(logging.INFO)

UPDATE_INVERVAL = 10 # update interval in seconds

DEFAULT_TEMP = 18
DEFAULT_BUFFER_BEER_TEMP = 0.5
DEFAULT_BUFFER_CHAMBER_SCALE = 5.0

class Chamber(threading.Thread):

    def __init__(self, _controller):
        threading.Thread.__init__(self)
        self.stopThread = True              # flag used for stopping the background thread
        self.controller = _controller
        self.tilt = None
        self.tempDates = [datetime.datetime.now()]
        self.targetTemps = [DEFAULT_TEMP]
        self.bufferBeerTemp = DEFAULT_BUFFER_BEER_TEMP
        self.bufferChamberScale = DEFAULT_BUFFER_CHAMBER_SCALE
        self.beerTemp = DEFAULT_TEMP
        self.chamberTemp = DEFAULT_TEMP


    # Starts the background thread
    def run(self):
        logger.info("Starting Chamber")
        self.stopThread = False
        
        while self.stopThread != True:
            self.control()
            time.sleep(UPDATE_INVERVAL)

        logger.info("Chamber Stopped")


    def __del__(self):
        logger.debug("Delete chamber class")


    def setControlTemps(self, _targetTemps, _tempDates, _bufferBeerTemp, _bufferChamberScale):
        self.targetTemps = _targetTemps
        self.tempDates = _tempDates
        self.bufferBeerTemp = _bufferBeerTemp
        self.bufferChamberScale = _bufferChamberScale

    
    def setTilt(self, _tilt):
        if _tilt is None:
            self.tilt = None
        else:
            self.tilt = _tilt


    def control(self):
        self.controller
        self.targetTemps
        self.tempDates
        self.bufferBeerTemp
        self.bufferChamberScale

        if self.tilt is not None:
            if self.tilt.isDataValid():
                self.beerTemp = self.tilt.getTemp()
        else:
            self.beerTemp = self.controller.getBeerTemp()

        self.chamberTemp = self.controller.getFridgeTemp()
    
        _curTime = datetime.datetime.now()
            
        # check which of the temperature change dates have passed
        x = -1
        for dt in self.tempDates:
            if dt < _curTime:
                x = x + 1
            
        # check if last date has been reached. If so, heating/cooling should stop
        if x == len(self.tempDates)-1:
            x = -2
        
        # No configured dates have passed, leave chamer powered off
        if x == -1:
            # Turn off heating and cooling
            self.controller.stopHeatingCooling
            logger.debug("Leaving chamber powered off until first date reached: " + self.tempDates[x+1].strftime("%d.%m.%Y %H:%M:%S"))
                
        elif x == -2:
            # Last configured date reached. Heating/cooling should be stopped
            self.controller.stopHeatingCooling
            logger.debug("Leaving chamber powered off; last date reached: " + self.tempDates[len(self.tempDates)-1].strftime("%d.%m.%Y %H:%M:%S"))

        elif x > -1:
            _target = self.targetTemps[x]
            if self.beerTemp > (_target + self.bufferBeerTemp) and (_target - self.chamberTemp) < self.bufferChamberScale*(self.beerTemp - _target):
                # Turn cooling ON
                self.controller.startCooling()
                logger.debug("Cooling to be turned ON - Target: " + str(_target) + "; Beer: " + str(self.beerTemp) + "; Chamber: " + str(self.chamberTemp) + "; Beer Buffer: " + str(self.bufferBeerTemp) + "; Chamber Scale: " + str(self.bufferChamberScale))

            elif self.beerTemp < (_target - self.bufferBeerTemp) and (self.chamberTemp - _target) < self.bufferChamberScale*(_target - self.beerTemp):
                # Turn heating ON
                self.controller.startHeating()
                logger.debug("Heating to be turned ON - Target: " + str(_target) + "; Beer: " + str(self.beerTemp) + "; Chamber: " + str(self.chamberTemp) + "; Beer Buffer: " + str(self.bufferBeerTemp) + "; Chamber Scale: " + str(self.bufferChamberScale))
            else:
                self.controller.stopHeatingCooling()
                logger.debug("No heating/cooling needed - Target: " + str(_target) + "; Beer: " + str(self.beerTemp) + "; Chamber: " + str(self.chamberTemp) + "; Beer Buffer: " + str(self.bufferBeerTemp) + "; Chamber Scale: " + str(self.bufferChamberScale))
        else:
            self.controller.stopHeatingCooling
            logger.error("Should never get here: x < -1")
        return  

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

