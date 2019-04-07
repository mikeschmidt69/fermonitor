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
logger.setLevel(logging.DEBUG)

CONFIGFILE = "fermonitor.ini"

DEFAULT_LOG_INTERVAL = 900
DEFAULT_TEMP = 18 # default target temperature in celcius
DEFAULT_BEER_TEMP_BUFFER = 0.5 # +/- degrees celcius beer is from target when heating/cooling will be turned on
DEFAULT_CHAMBER_SCALE_BUFFER = 5.0 # +/- degrees celcius chamber is from target when heating/cooling will be turned on
DEFAULT_ON_DELAY = 10 # default number of minutes fridge/heater should remain off before turning on again

CONTROL_TILT = 0
CONTROL_BEER = 1

def read():
    global sLogFile
    global iLogIntervalSeconds
    global sTiltColor
    global chamberControlTemp
    global bUseTilt
    global bUseLogFile
    global tempDates
    global temps
    global beerTempBuffer
    global chamberScaleBuffer
    global onDelay
    global logLevel
    global beerTempAdjust
    global chamberTempAdjust

    sLogFile = ""
    iLogIntervalSeconds = DEFAULT_LOG_INTERVAL
    chamberControlTemp = CONTROL_BEER
    onDelay = DEFAULT_ON_DELAY
    tempDates = []
    temps = []
    beerTempBuffer = DEFAULT_BEER_TEMP_BUFFER
    chamberScaleBuffer = DEFAULT_CHAMBER_SCALE_BUFFER
    onDelay = DEFAULT_ON_DELAY
    logLevel = logging.INFO

    bUseTilt = False
    bUseLogFile = False
    
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
        if config["LogFile"] != "":
            sLogFile = config.get("LogFile")
            bUseLogFile = True
        else:
            raise Exception
    except:
        logger.warning("Logfile not defined; data not logged to local file.")
        sLogFile = ""

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
            if config.get("ChamberControl") == "BEER":
                chamberControlTemp = CONTROL_BEER
            elif config.get("ChamberControl") == "TILT":
                chamberControlTemp = CONTROL_TILT
            else:
                chamberControlTemp = CONTROL_BEER
                logger.warning("Invalude ChamberControl configuration; using default: BEER")
        else:
            chamberControlTemp = CONTROL_BEER
            logger.warning("Invalude ChamberControl configuration; using default: BEER")
    except:
        chamberControlTemp = CONTROL_BEER
        logger.warning("Invalude ChamberControl configuration; using default: BEER")

    try:
        if config["Dates"] != "":
            dts = config["Dates"].split(",")
            for x in dts:
                tempDates.append(datetime.datetime.strptime(x, '%d/%m/%Y %H:%M:%S'))
        else:
            raise Exception
    except:
        tempDates = [datetime.datetime.now(),datetime.datetime.now()]
        logger.warning("Invalid date values; using default. Heating/cooling will NOT start")

    try:
        if config["Temps"] != "":
            t = config["Temps"].split(",")
            for x in t:
                temps.append(float(x))
        else:
            raise Exception
    except:
        temps = [DEFAULT_TEMP]
        logger.warning("Invalid temp values; using default: "+str(temps[0]))
        
    if len(tempDates) != len(temps)+1:
        tempDates = [datetime.datetime.now(),datetime.datetime.now()]
        temps = [DEFAULT_TEMP]
        logger.warning("Invalid date or time values; using default. Heating/cooling will NOT start")

    try:
        if config["BeerTemperatureBuffer"] != "" and float(config["BeerTemperatureBuffer"]) >= 0.0:
            beerTempBuffer = float(config.get("BeerTemperatureBuffer"))
        else:
            raise Exception
    except:
        beerTempBuffer = DEFAULT_BEER_TEMP_BUFFER
        logger.warning("Invalid beer temperature buffer in configuration; using default: "+str(beerTempBuffer))

    try:
        if config["ChamberScaleBuffer"] != "" and float(config["ChamberScaleBuffer"]) >= 0.0:
            chamberScaleBuffer = float(config.get("ChamberScaleBuffer"))
        else:
            raise Exception
    except:
        chamberScaleBuffer = DEFAULT_CHAMBER_SCALE_BUFFER
        logger.warning("Invalid chamber scale buffer in configuration; using default: "+str(chamberScaleBuffer))

    try:
        if config["BeerTempAdjust"] != "" and float(config["BeerTempAdjust"]) >= 0.0:
            beerTempAdjust = float(config.get("BeerTempAdjust"))
        else:
            raise Exception
    except:
        beerTempAdjust = 0.0
        logger.warning("Invalid BeerTempAdjust in configuration; using default: "+str(beerTempAdjust))

    try:
        if config["ChamberTempAdjust"] != "" and float(config["ChamberTempAdjust"]) >= 0.0:
            chamberTempAdjust = float(config.get("ChamberTempAdjust"))
        else:
            raise Exception
    except:
        chamberTempAdjust = 0.0
        logger.warning("Invalid BeerTempAdjust in configuration; using default: "+str(chamberTempAdjust))

    try:
        if config["OnDelay"] != "" and int(config["OnDelay"]) >= 0:
            onDelay = int(config.get("OnDelay"))
        else:
            raise Exception
    except:
        onDelay = DEFAULT_ON_DELAY
        logger.warning("Invalid OnDelay in configuration; using default: "+str(onDelay))


    try:
        if config["LogIntervalSeconds"] != "" and int(config.get("LogIntervalSeconds")) > 0:
            iLogIntervalSeconds = int(config.get("LogIntervalSeconds"))
        else:
            raise Exception
    except:
        iLogIntervalSeconds = DEFAULT_LOG_INTERVAL
        logger.warning("Problem reading logging interval from configuration file. Using default "+str(iLogIntervalSeconds)+"s if log file is defined.")

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

    st = "sLogFile: " + sLogFile +"\n"
    st = st + "sTiltColor: " + sTiltColor + "\n"
    st = st + "iLogIntervalSeconds: " + str(iLogIntervalSeconds) + "\n"
    st = st + "bUseTilt: " + str(bUseTilt) + "\n"
    st = st + "bUseLogFile: " + str(bUseLogFile) + "\n"
    st = st + "temps :"
    for x in temps:
        st = st + str(x) + ", "
    st = st + "\n"
    st = st + "dates :"
    for x in tempDates:
        st = st + str(x) + ", "
    st = st + "\n"
    st = st + "beerTempBuffer: " + str(beerTempBuffer) + "\n"
    st = st + "chamberScaleBuffer: " + str(chamberScaleBuffer) + "\n"
    st = st + "beerTempAdjust: " + str(beerTempAdjust) + "\n"
    st = st + "chamberTempAdjust: " + str(chamberTempAdjust)

    logger.debug("Result of reading fermonitor.ini:\n"+st)    
    return

