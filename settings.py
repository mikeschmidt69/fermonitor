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

import os
import datetime
import logging
from setup_logger import logger
import configparser

logger = logging.getLogger('FERMONITOR.CONFIG')
logger.setLevel(logging.INFO)

CONFIGFILE = "fermonitor.ini"

CONTROL_TILT = 0
CONTROL_WIRE = 1

def read():
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
        if config["TiltColor"] != "":
            sTiltColor = config.get("TiltColor")
            bUseTilt = True
        else:
            raise Exception
    except:
        bUseTilt = False
        logger.warning("No color specified for Tilt. Tilt not used.")
        sTiltColor = ""

    try:
        if config["ChamberControl"] != "":
            if config.get("ChamberControl") == "WIRE":
                chamberControlTemp = CONTROL_WIRE
            elif config.get("ChamberControl") == "TILT":
                chamberControlTemp = CONTROL_TILT
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

    st = "sTiltColor: " + sTiltColor + "\n"
    st = st + "bUseTilt: " + str(bUseTilt) + "\n"
    
    logger.debug("Result of reading fermonitor.ini:\n"+st)    
    return






