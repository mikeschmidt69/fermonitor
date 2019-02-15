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
import fridge
import tilt
import brewfather

logger = logging.getLogger('fermonitor')
logger.setLevel(logging.DEBUG)

def main():
    
    logger.info("Starting Fermonitor...")

    settings.init()
    fridge.init(settings.CONFIGFILE)
    
    # Start Tilt thread to read temp and gravity if tilt configuration file is specified
    if settings.bUseTilt:
        logger.debug("Starting Tilt Thread")
        tiltH = tilt.Tilt(settings.CONFIGFILE, settings.sTiltColor)
        tiltH.start()

    # Start BrewFather thread to store temp and gravity
    logger.debug("Starting BrewFather Thread")
    bf = brewfather.BrewFather(settings.CONFIGFILE)
    bf.start()

    # Create log file if specified and doesn't exist and write headings
    if settings.bUseLogFile and not os.path.exists(settings.sLogFile):
        logger.debug("Creating log file and writing headings")
        f = open(settings.sLogFile,"w")
        f.write("Device,Time,Temp,Gravity\n")
        f.close()

    device = None
    dataTime = None
    temp = None
    gravity = None

    timeLastLogged = None

    # Main loop for reading and logging data as well as controllng fermentor
    while True:

        if settings.bUseTilt:
            if tiltH.isDataValid():
                # read latest stored data from tilt
                logger.debug("Reading data from Tilt")
                device = "Tilt_"+tiltH.getColor()
                temp = tiltH.getTemp()
                gravity = tiltH.getGravity()
                dataTime = tiltH.timeOfData() # time is used to tell if new data is available or not

        # Only log if there is data
        if device != None and dataTime != None and temp != None and gravity != None:
            # seed latest data to BrewFather. This data may or may not reach the BrewFather app depending on update interval
            logger.debug("Sending data to BrewFather")
            bf.setData(device, temp, gravity, dataTime)
            
            if settings.bUseLogFile:
                curTime = datetime.datetime.now()

                # Only log if first log or (logging interval has experied and there is new data)
                if timeLastLogged == None or \
                    (curTime > timeLastLogged + datetime.timedelta(seconds=settings.iLogIntervalSeconds) and dataTime > timeLastLogged):

                    logger.debug("Logging data to CSV file")

                    sTemp = str(round(float(temp),1))
                    sGravity = "{:5.3f}".format(round(float(gravity),3))
                    sTime = dataTime.strftime("%d.%m.%Y %H:%M:%S")
               
                    f= open(settings.sLogFile,"a")
                    f.write(device + ", " + sTime + "," + sTemp + "," + sGravity +"\n")
                    f.close()
                
                timeLastLogged = dataTime

            fridge.control(temp)

        time.sleep(10)

if __name__ == "__main__": #dont run this as a module

    try:
        main()

    except KeyboardInterrupt:
        print("...Fermonitor Stopped")
    
