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
import configparser

from flask import Flask, render_template                                                         
import threading

import chamber
import interface
import tilt
import brewfather

logger = logging.getLogger('FERMONITOR')
logger.setLevel(logging.INFO)

CONFIGFILE = "fermonitor.ini"

CONTROL_TILT = 0
CONTROL_WIRE = 1

timeBeer = None
target = None
tempBeer = None
tempChamber = None
tempBeerWire = None
gravity = None

cTilt = None


def read_settings():
    global sTiltColor
    global chamberControlTemp
    global bUseTilt
    global logLevel

    chamberControlTemp = CONTROL_WIRE
    bUseTilt = False
    logLevel = logging.INFO
    
    logger.debug("Reading configfile: "+ CONFIGFILE)

    try:
        if os.path.isfile(CONFIGFILE) == False:
            raise Exception
    
        ini = configparser.ConfigParser()
        ini.read(CONFIGFILE)
    except:
        raise IOError("Fermonitor configuration file is not valid: "+CONFIGFILE)

    try:
        config = ini['Fermonitor']
    except:
        raise IOError("[Fermonitor] section not found in fermonitor.ini")

    try:
        if config["MessageLevel"] == "DEBUG":
            logLevel = logging.DEBUG
        elif config["MessageLevel"] == "WARNING":
            logLevel = logging.WARNING
        elif config["MessageLevel"] == "ERROR":
            logLevel = logging.ERROR
        elif config["MessageLevel"] == "INFO":
            logLevel = logging.INFO
        else:
            logLevel = logging.INFO
    except KeyError:
        logLevel = logging.INFO

    logger.setLevel(logLevel)   

    try:
        if config["TiltColor"] != "":
            sTiltColor = config.get("TiltColor")
        else:
            raise Exception
    except:
        logger.warning("No color specified for Tilt. Tilt not used.")
        sTiltColor = ""

    logger.debug("Tilt color: "+ sTiltColor)    

    try:
        if config["ChamberControl"] != "":
            if config.get("ChamberControl") == "WIRE":
                chamberControlTemp = CONTROL_WIRE
                logger.debug("Chamber control temperature based on WIRE")    
            elif config.get("ChamberControl") == "TILT":
                chamberControlTemp = CONTROL_TILT
                logger.debug("Chamber control temperature based on TILT")    
            else:
                chamberControlTemp = CONTROL_WIRE
                logger.warning("Invalid ChamberControl configuration; using default: WIRE")
        else:
            chamberControlTemp = CONTROL_WIRE
            logger.warning("Invalid ChamberControl configuration; using default: WIRE")
    except:
        chamberControlTemp = CONTROL_WIRE
        logger.warning("Invalid ChamberControl configuration; using default: WIRE")

    try:
        if config["MessageLevel"] == "DEBUG":
            logLevel = logging.DEBUG
        elif config["MessageLevel"] == "WARNING":
            logLevel = logging.WARNING
        elif config["MessageLevel"] == "ERROR":
            logLevel = logging.ERROR
        elif config["MessageLevel"] == "INFO":
            logLevel = logging.INFO
        else:
            logLevel = logging.INFO
    except KeyError:
        logLevel = logging.INFO

    logger.setLevel(logLevel)   

    logger.debug("Completed reading settings")    
    return


################################################################
def main():
    
    global timeBeer
    global target
    global tempBeer
    global tempChamber
    global tempBeerWire
    global gravity
    global cTilt


    logger.info("Starting Fermonitor...")

    read_settings()

    cInterface = interface.Interface("Fermonitor......")
    cInterface.setLogLevel(logLevel)
    cInterface.start()

    cChamber = chamber.Chamber(None)
    cChamber.start()

    cTilt = None

    # Start BrewFather thread to store temp and gravity
    logger.debug("Starting BrewFather Thread")
    cBrewfather = brewfather.BrewFather()
    cBrewfather.start()

    # Main loop for reading and logging data as well as controllng fermentor
    while True:

        read_settings()
        cInterface.setLogLevel(logLevel)

        # Handle Tilt
        
        if sTiltColor != "":
            if (cTilt is not None) and (cTilt.getColor() != sTiltColor):
                logger.debug("Tilt color changed: stopping Tilt: " + cTilt.getColor())
                cTilt = None

            if cTilt is None:
                logger.debug("Starting Tilt monitoring: " + sTiltColor)
                cTilt = tilt.Tilt(sTiltColor)
                cTilt.start()
                time.sleep(10)

        else:
            cTilt = None

        if chamberControlTemp == CONTROL_TILT:
            cChamber.setTilt(cTilt)
        else:
            cChamber.setTilt(None)

        if not cChamber.paused:
            target = cChamber.getTargetTemp()
            tempBeer = cChamber.getBeerTemp()
            tempBeerWire = cChamber.getWireBeerTemp()
            tempChamber = cChamber.getChamberTemp()
            timeBeer = cChamber.timeOfData()
            if cTilt is not None and cTilt.isDataValid():
                gravity = cTilt.getGravity()
            else:
                gravity = None

            cBrewfather.setData(tempBeer, tempChamber, gravity)        

            cInterface.setData( target, tempBeer, gravity, tempBeerWire, tempChamber)

        else:
            timeBeer = None
            target = None
            tempBeer = None
            tempChamber = None
            tempBeerWire = None

        time.sleep(1)

app = Flask(__name__)
@app.route("/", methods=["GET","POST"])
def index():
    data = {}

    if timeBeer is not None:
        data['timeBeer'] = timeBeer.strftime("%d.%m.%Y %H:%M:%S")
    if target is not None:
        data['target'] = str(round(float(target),1))
    if tempBeer is not None and cTilt is not None:
        data['tempBeer'] = str(round(float(tempBeer),1))
    if tempBeerWire is not None and tempBeer != tempBeerWire:
        data['tempBeerWire'] = str(round(float(tempBeerWire),1))
    if tempChamber is not None:
        data['tempChamber'] = str(round(float(tempChamber),1))
    if gravity is not None:
        data['gravity'] = "{:5.3f}".format(round(float(gravity),3))

    return render_template('index.html', data=data)

if __name__ == "__main__": #dont run this as a module

    try:
        threading.Thread(target=app.run, args=('0.0.0.0','5000',False)).start()
        main()

    except KeyboardInterrupt:
        print("...Fermonitor Stopped")
 
