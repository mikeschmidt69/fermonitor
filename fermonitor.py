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

from urllib import request, parse
import json
import sys
import requests
import datetime
import time
import os
import logging
from setup_logger import logger
import configparser
from distutils.util import strtobool
import settings
import chamber
import tilt
import brewfather
import onewiretemp

logger = logging.getLogger('fermonitor')
logger.setLevel(logging.DEBUG)

def main():
    
    logger.info("Starting Fermonitor...")

    settings.init()
    tempChamber = chamber.Chamber(settings.CONFIGFILE)
    
    # Start Tilt thread to read temp and gravity if tilt configuration file is specified
    if settings.bUseTilt:
        logger.debug("Starting Tilt Thread")
        tiltH = tilt.Tilt(settings.CONFIGFILE, settings.sTiltColor)
        tiltH.start()

    # Start BrewFather thread to store temp and gravity
    logger.debug("Starting BrewFather Thread")
    bf = brewfather.BrewFather(settings.CONFIGFILE)
    bf.start()

    # Start one-wire temperature sensor reading
    tempSensor = onewiretemp.OneWireTemp(settings.CONFIGFILE)
    tempSensor.start()

    # Create log file if specified and doesn't exist and write headings
    if settings.bUseLogFile and not os.path.exists(settings.sLogFile):
        logger.debug("Creating log file and writing headings")
        f = open(settings.sLogFile,"w")
        f.write("Tilt Time,Tilt Temp,OneWire Time,OneWire Temp,Gravity\n")
        f.close()

    timeTilt = None
    tempTilt = None
    gravity = None
    tempOneWire = None
    timeOneWire = None

    timeLastLogged = None

    beer_temp = None
    beer_time = None
    aux_temp = None

    # Main loop for reading and logging data as well as controllng fermentor
    while True:

        if settings.bUseTilt:
            if tiltH.isDataValid():
                # read latest stored data from tilt
                logger.debug("Reading data from Tilt")
                tempTilt = tiltH.getTemp()
                gravity = tiltH.getGravity()
                timeTilt = tiltH.timeOfData() # time is used to tell if new data is available or not

        if tempSensor.isDataValid():
            tempOneWire = tempSensor.getTemp()
            timeOneWire = tempSensor.timeOfData()

        if settings.oneWireTempMeasure == settings.MEASURE_BEER and settings.chamberControlTemp == settings.CONTROL_ONEWIRETEMP:
            beer_temp = tempOneWire
            beer_time = timeOneWire
        else:
            beer_temp = tempTilt
            beer_time = timeTilt

        if settings.oneWireTempMeasure == settings.MEASURE_CHAMBER:
            aux_temp = tempOneWire

        if (beer_temp != None or gravity != None) and beer_time != None:
            bf.setData(beer_temp, aux_temp, gravity, beer_time)
                
        if settings.bUseLogFile:
            curTime = datetime.datetime.now()

            # Only log if first log or (logging interval has experied and there is new data)
            if timeLastLogged == None or \
                (curTime > timeLastLogged + datetime.timedelta(seconds=settings.iLogIntervalSeconds) and \
                     (timeTilt > timeLastLogged or timeOneWire > timeLastLogged)):

                logger.debug("Logging data to CSV file")

                f= open(settings.sLogFile,"a")
                f.write(timeTilt.strftime("%d.%m.%Y %H:%M:%S") + "," \
                    + str(round(float(tempTilt),1)) + "," + timeOneWire.strftime("%d.%m.%Y %H:%M:%S") + "," \
                        + str(round(float(tempOneWire),1)) + "," + "{:5.3f}".format(round(float(gravity),3)) +"\n")
                f.close()
                
                timeLastLogged = curTime

        tempChamber.control(beer_temp)

        time.sleep(10)

if __name__ == "__main__": #dont run this as a module

    try:
        main()

    except KeyboardInterrupt:
        print("...Fermonitor Stopped")
 
    
