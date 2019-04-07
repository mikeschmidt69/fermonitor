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
import controller
import tilt
import brewfather

logger = logging.getLogger('FERMONITOR')
logger.setLevel(logging.INFO)

control = controller.Controller()
chamber = chamber.Chamber(control)

################################################################
def main():
    
    logger.info("Starting Fermonitor...")

    settings.read()
    chamber.setLogLevel(settings.logLevel)
    control.setLogLevel(settings.logLevel)
        
    # Start Tilt thread to read temp and gravity if tilt configuration file is specified
    if settings.bUseTilt:
        logger.debug("Starting Tilt Thread")
        tiltH = tilt.Tilt(settings.CONFIGFILE, settings.sTiltColor)
        tiltH.start()
        time.sleep(10)
        if settings.chamberControlTemp == settings.CONTROL_TILT:
            chamber.setTilt(tiltH)

    control.start()
    control.setConfig(settings.onDelay, settings.beerTempAdjust, settings.chamberTempAdjust)
    time.sleep(5)
    chamber.setControlTemps(settings.temps,settings.tempDates,settings.beerTempBuffer, settings.chamberScaleBuffer)
    chamber.start()

    # Start BrewFather thread to store temp and gravity
    logger.debug("Starting BrewFather Thread")
    bf = brewfather.BrewFather(settings.CONFIGFILE)
    bf.start()
    
    timeTilt = None
    tempTilt = None
    gravity = None
    tempBeer = None
    tempChamber = None
    timeBeer = None

    timeLastLogged = None

    beer_temp = None
    beer_time = None
    aux_temp = None

    # Main loop for reading and logging data as well as controllng fermentor
    while True:

        # Create log file if specified and doesn't exist and write headings
        if settings.bUseLogFile and not os.path.exists(settings.sLogFile):
            logger.debug("Creating log file and writing headings")
            f = open(settings.sLogFile,"w")
            f.write("Tilt Time,Tilt Temp,Controller Time,Beer Temp, Chamber Temp, Gravity\n")
            f.close()

        if settings.bUseTilt:
            if tiltH.isDataValid():
                # read latest stored data from tilt
                logger.debug("Reading data from Tilt")
                tempTilt = tiltH.getTemp()
                gravity = tiltH.getGravity()
                timeTilt = tiltH.timeOfData() # time is used to tell if new data is available or not
        else:
            chamber.setTilt(None)

        tempBeer = control.getBeerTemp()
        tempChamber = control.getFridgeTemp()
        timeBeer = control.timeOfData()

        if settings.chamberControlTemp == settings.CONTROL_BEER:
            beer_temp = tempBeer
            beer_time = timeBeer
            chamber.setTilt(None)
        elif settings.chamberControlTemp == settings.CONTROL_TILT and settings.bUseTilt:
            beer_temp = tempTilt
            beer_time = timeTilt
            chamber.setTilt(tiltH)

        aux_temp = tempChamber

        if (beer_temp != None or gravity != None or aux_temp != None) and beer_time != None:
            bf.setData(beer_temp, aux_temp, gravity, beer_time)
                
        if settings.bUseLogFile:
            curTime = datetime.datetime.now()

            # Only log if first log or (logging interval has experied and there is new data)
            if timeLastLogged == None or \
                (curTime > timeLastLogged + datetime.timedelta(seconds=settings.iLogIntervalSeconds) and \
                     ((timeTilt != None and timeTilt > timeLastLogged) or (timeBeer != None and timeBeer > timeLastLogged))):

                logger.debug("Logging data to CSV file")

                outstr = ""
                if timeTilt != None:
                    outstr = outstr + timeTilt.strftime("%d.%m.%Y %H:%M:%S")
                outstr = outstr + ","
                
                if tempTilt != None:
                    outstr = outstr + str(round(float(tempTilt),1))
                outstr = outstr + ","
                
                if timeBeer != None:
                    outstr = outstr + timeBeer.strftime("%d.%m.%Y %H:%M:%S")
                outstr = outstr + ","

                if tempBeer != None:
                    outstr = outstr + str(round(float(tempBeer),1))
                outstr = outstr + ","

                if tempChamber != None:
                    outstr = outstr + str(round(float(tempChamber),1))
                outstr = outstr + ","

                if gravity != None:
                    outstr = outstr + "{:5.3f}".format(round(float(gravity),3))
                outstr = outstr + "\n"

                f= open(settings.sLogFile,"a")
                f.write(outstr)
                f.close()
                logger.info("CSV ("+curTime.strftime("%d.%m.%Y %H:%M:%S")+"): "+outstr.strip("\n"))
                timeLastLogged = curTime

        time.sleep(10)

        settings.read()
        # update parameters
        logger.setLevel(settings.logLevel)
        chamber.setControlTemps(settings.temps, settings.tempDates, settings.beerTempBuffer, settings.chamberScaleBuffer)
        chamber.setLogLevel(settings.logLevel)
        control.setLogLevel(settings.logLevel)
        control.setConfig(settings.onDelay, settings.beerTempAdjust, settings.chamberTempAdjust)


if __name__ == "__main__": #dont run this as a module

    try:
        main()

    except KeyboardInterrupt:
        print("...Fermonitor Stopped")
 
    
