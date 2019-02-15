import sys
import os
import datetime
import logging
from setup_logger import logger
import configparser

logger = logging.getLogger('ferment.config')
logger.setLevel(logging.DEBUG)

CONFIGFILE = "fermonitor.ini"

DEFAULT_LOG_INTERVAL = 900

def init():
    global sLogFile
    global iLogIntervalSeconds
    global sTiltColor

    global bUseTilt
    global bUseLogFile

    sLogFile = ""
    iLogIntervalSeconds = DEFAULT_LOG_INTERVAL
    sTiltConf = ""

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
        logger.warning("No color specified for Tilt: " + sTiltConf + ". Tilt not used.")
        sTiltColor = ""
    
    try:
        if config["LogIntervalSeconds"] != "" and int(config.get("LogIntervalSeconds")) > 0:
            iLogIntervalSeconds = int(config.get("LogIntervalSeconds"))
        else:
            raise Exception
    except:
        iLogIntervalSeconds = DEFAULT_LOG_INTERVAL
        logger.warning("Problem reading logging interval from configuration file. Using default "+str(iLogIntervalSeconds)+"s if log file is defined.")
        
    st = "sLogFile: " + sLogFile +"\n"
    st = st + "sTiltConf: " + sTiltConf + "\n"
    st = st + "iLogIntervalSeconds: " + str(iLogIntervalSeconds) + "\n"
    st = st + "bUseTilt: " + str(bUseTilt) + "\n"
    st = st + "bUseLogFile: " + str(bUseLogFile)
    logger.debug("Result of reading fermonitor.ini:\n"+st)    
    return

