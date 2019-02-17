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
DEFAULT_COOLING_ON_DELAY = 10
DEFAULT_HEATING_ON_DELAY = 10

INVALID_GPIO = -1

class Chamber:

    def __init__(self, _config):
        self.config = _config
        self.tempDates = []
        self.temps = []
        self.coolingOnDelay = DEFAULT_COOLING_ON_DELAY # interval in minutes between powering off and on cooling source
        self.heatingOnDelay = DEFAULT_HEATING_ON_DELAY # interval in minutes between powering off and on heating source
        self.isCooling = False
        self.isHeating = False
        self.timeCoolingOff = datetime.datetime.now()-datetime.timedelta(minutes=DEFAULT_COOLING_ON_DELAY)
        self.timeHeatinggOff = datetime.datetime.now()-datetime.timedelta(minutes=DEFAULT_HEATING_ON_DELAY)
        self.coolingGPIO = INVALID_GPIO
        self.heatingGPIO = INVALID_GPIO
    
        # Set the GPIO naming conventions
        GPIO.setmode (GPIO.BCM)
        GPIO.setwarnings(False)

        self._readConf()

    def __del__(self):
        GPIO.cleanup()

    def control(self, _temp):
        self.coolingOnDelay
        self.heatingOnDelay
        self.isCooling
        self.isHeating
        self.timeCoolingOff
        self.timeHeatinggOff
        self.tempDates
        self.temps
        self.coolingGPIO
        self.heatingGPIO
    
        _curTime = datetime.datetime.now()
    
        self._readConf()
        
        # check which of the temperature change dates have passed
        x = -1
        for dt in self.tempDates:
            if dt < _curTime:
                x = x + 1
        
        # No configured dates have passed, leave chamer powered off
        if x == -1:
            self._setPower(False, False)
            logger.debug("Leaving chamber powered off until first date reached: " + self.tempDates[x+1].strftime("%d.%m.%Y %H:%M:%S"))
                
        elif x > -1:
            _target = self.temps[x]
            if _temp > _target and self.coolingGPIO != INVALID_GPIO:
                if self.isCooling == False and _curTime < self.timeCoolingOff + datetime.timedelta(minutes=self.coolingOnDelay):
                    logger.debug("T: "+str(_temp)+" is higer than target: "+str(_target)+" but cooling cannot be turned on yet.")
                else:
                    # Turn cooling ON and ensure heating is OFF
                    self._setPower(True, False)
                    logger.debug("Cooling turned ON - T: "+str(_temp)+" is higer than target: "+str(_target))

            elif _temp < _target and self.heatingGPIO != INVALID_GPIO:
                if self.isHeating == False and _curTime < self.timeHeatinggOff + datetime.timedelta(minutes=self.heatingOnDelay):
                    logger.debug("T: "+str(_temp)+" is lower than target: "+str(_target)+" but heating cannot be turned on yet.")
                else:
                    # Turn heating ON and ensure cooling is OFF
                    self._setPower(False, True)
                    logger.debug("Heating turned ON - T: "+str(_temp)+" is higer than target: "+str(_target))
            else:
                self._setPower(False, False)
                logger.debug("Chamber is at right setting or lacking nesessary heating/cooling capabilities. T: "+str(_temp)+" Target: "+str(_target))
        else:
            logger.debug("Should never get here: x < -1")
        return  


    def _setPower(self, _turnOnCooling, _turnOnHeating):
        if self.heatingGPIO != INVALID_GPIO:
            if _turnOnHeating:
                GPIO.output(self.heatingGPIO, GPIO.HIGH)
                self.isHeating = True
            else:
                GPIO.output(self.heatingGPIO, GPIO.LOW)
                if self.isHeating:
                    self.timeHeatingOff = datetime.datetime.now()
                    self.isHeating = False
        if self.coolingGPIO != INVALID_GPIO:
            if _turnOnCooling:
                GPIO.output(self.coolingGPIO, GPIO.HIGH)
                self.isCooling = True
            else:
                GPIO.output(self.coolingGPIO, GPIO.LOW)
                if self.isCooling:
                    self.timeCoolingOff = datetime.datetime.now()
                    self.isCooling = False
        return

    def _readConf(self):
        self.tempDates
        self.temps
        self.config
        self.coolingOnDelay
        self.heatingOnDelay

        self.tempDates = []
        self.temps = []

        logger.debug("Reading chamber settings: "+ self.config)
        try:
            if os.path.isfile(self.config) == False:
                raise Exception
    
            ini = configparser.ConfigParser()
            ini.read(self.config)
        except:
            raise IOError("Fermonitor configuration file is not valid: "+self.config)
        
        try:
            config = ini['Chamber']
        except:
            raise IOError("[Chamber] section not found in fermonitor.ini")

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
            if config["CoolOnDelay"] != "" and int(config["CoolOnDelay"]) >= 0:
                self.coolingOnDelay = int(config.get("CoolOnDelay"))
            else:
                raise Exception
        except:
            self.coolingOnDelay = DEFAULT_COOLING_ON_DELAY
            logger.warning("Invalid CoolOnDelay in configuration; using default: "+str(self.coolingOnDelay))

        try:
            if config["HeatOnDelay"] != "" and int(config["HeatOnDelay"]) >= 0:
                self.heatingOnDelay = int(config.get("HeatOnDelay"))
            else:
                raise Exception
        except:
            self.heatingOnDelay = DEFAULT_HEATING_ON_DELAY
            logger.warning("Invalid HeatOnDelay in configuration; using default: "+str(self.heatingOnDelay))

        try:
            if config["CoolingGPIO"] != "" and int(config["CoolingGPIO"]) >= 0:
                pin = int(config.get("CoolingGPIO"))
                if pin != self.coolingGPIO:
                    self._setPower(False, False)
                    self.coolingGPIO = pin
                    GPIO.setup(self.coolingGPIO, GPIO.OUT)
                    self._setPower(False, False)
                    self.timeCoolingOff = datetime.datetime.now()-datetime.timedelta(minutes=self.coolingOnDelay)                
            else:
                raise Exception
        except:
            self.coolingGPIO = INVALID_GPIO
            logger.warning("Invalid or missing CoolingGPIO configuration; cooling device is not used.")

        try:
            if config["HeatingGPIO"] != "" and int(config["HeatingGPIO"]) >= 0:
                pin = int(config.get("HeatingGPIO"))
                if pin != self.heatingGPIO:
                    self._setPower(False, False)
                    self.heatingGPIO = pin
                    GPIO.setup(self.heatingGPIO, GPIO.OUT)
                    self._setPower(False, False)
                    self.timeHeatingOff = datetime.datetime.now()-datetime.timedelta(minutes=self.coolingOnDelay)
            else:
                raise Exception
        except:
            self.heatinggGPIO = INVALID_GPIO
            logger.warning("Invalid or missing HeatingGPIO configuration; heating device is not used.")

        return

