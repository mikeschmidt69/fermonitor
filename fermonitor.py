# MIT License
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

import sys
import datetime
import time
import os
import logging
from setup_logger import logger
from distutils.util import strtobool
import settings

import chamber
import interface
import tilt
import brewfather

logger = logging.getLogger('FERMONITOR')
logger.setLevel(logging.INFO)

################################################################
def main():
    
    logger.info("Starting Fermonitor...")

    cInterface = interface.Interface("Fermonitor......")

    settings.read()

    cInterface.setLogLevel(settings.logLevel)
    cInterface.start()

    cChamber = None
    cTilt = None
        
    # Start Tilt thread to read temp and gravity if tilt configuration file is specified
    if settings.bUseTilt:
        logger.debug("Starting Tilt Thread")
        cTilt = tilt.Tilt(settings.sTiltColor)
        cTilt.start()
        time.sleep(10)
        if settings.chamberControlTemp == settings.CONTROL_TILT:
            cChamber = chamber.Chamber(cTilt)

    if cChamber == None:
        cChamber = chamber.Chamber(None)
    
    cChamber.start()

    # Start BrewFather thread to store temp and gravity
    logger.debug("Starting BrewFather Thread")
    cBrewfather = brewfather.BrewFather()
    cBrewfather.start()
    
    gravity = None
    tempBeer = None
    tempChamber = None
    timeBeer = None


    # Main loop for reading and logging data as well as controllng fermentor
    while True:

        target = cChamber.getTargetTemp()
        tempBeer = cChamber.getBeerTemp()
        gravity = cChamber.getBeerSG()
        tempBeerWireTemp = cChamber.getWireBeerTemp()
        tempChamber = cChamber.getChamberTemp()
        timeBeer = cChamber.timeOfData()

        cBrewfather.setData(tempBeer, tempChamber, gravity, timeBeer)        

        cInterface.setData( target, tempBeer, gravity, tempBeerWireTemp, tempChamber)

        time.sleep(1)


if __name__ == "__main__": #dont run this as a module

    try:
        main()

    except KeyboardInterrupt:
        print("...Fermonitor Stopped")
 
    
