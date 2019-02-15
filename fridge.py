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

logger = logging.getLogger('fridge')
logger.setLevel(logging.INFO)

DEFAULT_TEMP = 18
DEFAULT_POWER_ON_DELAY = 10

isFridgeOn = False
timeFridgeOff = datetime.datetime.now()-datetime.timedelta(minutes=DEFAULT_POWER_ON_DELAY)

def init(config):
    global fridgeConfig
    global tempDates
    global temps
    global powerOnDelay

    fridgeConfig = config
    tempDates = []
    temps = []
    powerOnDelay = DEFAULT_POWER_ON_DELAY # interval in minutes between powering off and on fridge

def control(temp):

    global timeFridgeOff
    global isFridgeOn
    global tempDates
    global temps
    global powerOnDelay
    global fridgeConfig
    
    curTime = datetime.datetime.now()
    
    readFridgeSettings()

    x = -1
        
    # check which of the temperature change dates have passed
    for dt in tempDates:
        if dt < curTime:
            x = x + 1
        
    if x == -1:
#       # Turn fridge OFF until first date is reached
        isFridgeOn = False
        logger.debug("Leaving fridge off until first date reached: " + tempDates[x+1].strftime("%d.%m.%Y %H:%M:%S"))
                
    elif x > -1:
        target = temps[x]
        if temp >= target and isFridgeOn == False:
            if curTime < timeFridgeOff + datetime.timedelta(minutes=powerOnDelay):
                logger.debug("T: "+str(temp)+" is higer or equal to target: "+str(target)+" but cannot be turned on yet.")
            else:
#               # Turn fridge ON
                isFridgeOn = True
                logger.debug("Fridge turned ON - T: "+str(temp)+" is higer or equal to target: "+str(target))
        elif temp < target and isFridgeOn:
#           # Turn fridge OFF
            isFridgeOn = False
            logger.debug("Fridge turned OFF - T: "+str(temp)+" is lower than target: "+str(target))
            timeFridgeOff = curTime
        else:
            logger.debug("Fridge is at right setting: "+str(isFridgeOn)+" T: "+str(temp)+" Target: "+str(target))
    else:
        logger.debug("Should never get here: x < -1")
    return  

def readFridgeSettings():
    global tempDates
    global temps
    global fridgeConfig
    global powerOnDelay

    tempDates = []
    temps = []

    logger.debug("Reading fridge settings: "+ fridgeConfig)
    try:
        if os.path.isfile(fridgeConfig) == False:
            raise Exception
    
        ini = configparser.ConfigParser()
        ini.read(fridgeConfig)
    except:
        raise IOError("Fermonitor configuration file is not valid: "+fridgeConfig)
        
    try:
        config = ini['Fridge']
    except:
        raise IOError("[Fridge] section not found in fermonitor.ini")
    
    try:
        if config["MessageLevel"] == "DEBUG":
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)
    except KeyError:
        logger.setLevel(logging.INFO)
    
    try:
        if config["Dates"] != "":
            dts = config["Dates"].split(",")
            for x in dts:
                tempDates.append(datetime.datetime.strptime(x, '%d/%m/%Y %H:%M:%S'))
        else:
            raise Exception
    except:
        tempDates = [datetime.datetime.now()]
        logger.warning("Invalid date values; using default: "+tempDates[0].strftime("%d.%m.%Y %H:%M:%S"))

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
        
    if len(tempDates) != len(temps):
        tempDates = [datetime.datetime.now()]
        temps = [DEFAULT_TEMP]
        logger.warning("Temp and dates have different quantities; setting both to defaults: "+str(temps[0])+"/"+tempDates[0].strftime("%d.%m.%Y %H:%M:%S"))

    try:
        if config["PowerOnDelay"] != "" and int(config["PowerOnDelay"]) > 0:
            powerOnDelay = int(config.get("PowerOnDelay"))
        else:
            raise Exception
    except:
        powerOnDelay = DEFAULT_POWER_ON_DELAY
        logger.warning("Invalid power on delay; using default: "+str(powerOnDelay))

    return

