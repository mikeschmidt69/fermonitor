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
import RPi.GPIO as GPIO
import logging
from setup_logger import logger
import configparser

logger = logging.getLogger('fridge')
logger.setLevel(logging.INFO)

# Initialize the GPIO Pins
os.system('modprobe w1-gpio') # Turns on the GPIO module

DEFAULT_TEMP = 18
DEFAULT_POWER_ON_DELAY = 10

class Fridge:

    def __init__(self, config):
        self.fridgeConfig = config
        self.tempDates = []
        self.temps = []
        self.powerOnDelay = DEFAULT_POWER_ON_DELAY # interval in minutes between powering off and on fridge
        self.isFridgeOn = False
        self.timeFridgeOff = datetime.datetime.now()-datetime.timedelta(minutes=DEFAULT_POWER_ON_DELAY)
        self.relayPin = -1
        self.useFridge = False

        # Set the GPIO naming conventions
        GPIO.setmode (GPIO.BCM)
        GPIO.setwarnings(False)

        self._readConf()

    def __del__(self):
        GPIO.cleanup()

    def control(self, temp):
        self.timeFridgeOff
        self.isFridgeOn
        self.tempDates
        self.temps
        self.powerOnDelay
        self.fridgeConfig
    
        curTime = datetime.datetime.now()
    
        self._readConf()

        x = -1
        
        # check which of the temperature change dates have passed
        for dt in self.tempDates:
            if dt < curTime:
                x = x + 1
        
        if x == -1:
            # Turn fridge OFF until first date is reached
            self._powerFridge(False)
            logger.debug("Leaving fridge off until first date reached: " + self.tempDates[x+1].strftime("%d.%m.%Y %H:%M:%S"))
                
        elif x > -1:
            target = self.temps[x]
            if temp >= target and self.isFridgeOn == False:
                if curTime < self.timeFridgeOff + datetime.timedelta(minutes=self.powerOnDelay):
                    logger.debug("T: "+str(temp)+" is higer or equal to target: "+str(target)+" but cannot be turned on yet.")
                else:
                    # Turn fridge ON
                    self._powerFridge(True)
                    logger.debug("Fridge turned ON - T: "+str(temp)+" is higer or equal to target: "+str(target))
            elif temp < target and self.isFridgeOn:
                # Turn fridge Off
                self._powerFridge(False)
                logger.debug("Fridge turned OFF - T: "+str(temp)+" is lower than target: "+str(target))
            else:
                logger.debug("Fridge is at right setting: "+str(self.isFridgeOn)+" T: "+str(temp)+" Target: "+str(target))
        else:
            logger.debug("Should never get here: x < -1")
        return  


    def _powerFridge(self, turnOn):
        if self.useFridge:
            if turnOn:
                GPIO.output(self.relayPin, GPIO.HIGH)
                self.isFridgeOn = True
            else:
                GPIO.output(self.relayPin, GPIO.LOW)
                self.timeFridgeOff = datetime.datetime.now()
                self.isFridgeOn = False
        return

    def _readConf(self):
        self.tempDates
        self.temps
        self.fridgeConfig
        self.powerOnDelay

        self.tempDates = []
        self.temps = []

        logger.debug("Reading fridge settings: "+ self.fridgeConfig)
        try:
            if os.path.isfile(self.fridgeConfig) == False:
                raise Exception
    
            ini = configparser.ConfigParser()
            ini.read(self.fridgeConfig)
        except:
            raise IOError("Fermonitor configuration file is not valid: "+self.fridgeConfig)
        
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
                    self.tempDates.append(datetime.datetime.strptime(x, '%d/%m/%Y %H:%M:%S'))
            else:
                raise Exception
        except:
            self.tempDates = [datetime.datetime.now()]
            logger.warning("Invalid date values; using default: "+self.tempDates[0].strftime("%d.%m.%Y %H:%M:%S"))

        try:
            if config["Temps"] != "":
                t = config["Temps"].split(",")
                for x in t:
                    self.temps.append(float(x))
            else:
                raise Exception
        except:
            self.temps = [DEFAULT_TEMP]
            logger.warning("Invalid temp values; using default: "+str(self.temps[0]))
        
        if len(self.tempDates) != len(self.temps):
            self.tempDates = [datetime.datetime.now()]
            self.temps = [DEFAULT_TEMP]
            logger.warning("Temp and dates have different quantities; setting both to defaults: "+str(self.temps[0])+"/"+self.tempDates[0].strftime("%d.%m.%Y %H:%M:%S"))

        try:
            if config["PowerOnDelay"] != "" and int(config["PowerOnDelay"]) > 0:
                self.powerOnDelay = int(config.get("PowerOnDelay"))
            else:
                raise Exception
        except:
            self.powerOnDelay = DEFAULT_POWER_ON_DELAY
            logger.warning("Invalid power on delay; using default: "+str(self.powerOnDelay))

        try:
            if config["RelayGPIO"] != "" and int(config["RelayGPIO"]) > 0:
                pin = int(config.get("RelayGPIO"))
                if pin != self.relayPin:
                    self._powerFridge(False)
                    self.relayPin = pin
                    GPIO.setup(self.relayPin, GPIO.OUT)
                    GPIO.output(self.relayPin, GPIO.LOW)
                    self.timeFridgeOff = datetime.datetime.now()-datetime.timedelta(minutes=self.powerOnDelay)
                
                self.useFridge = True
            else:
                raise Exception
        except:
            self.relayPin = -1
            self.useFridge = False
            logger.warning("Invalid or missing GPIO configuration for fridge relay switch; fridge not used.")

        return

