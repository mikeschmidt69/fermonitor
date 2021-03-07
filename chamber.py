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
import threading
import datetime
import time

import logging

import tilt
import configparser
import RPi.GPIO as GPIO

logger = logging.getLogger('FERMONITOR.CHAMBER')
logger.setLevel(logging.INFO)

UPDATE_INVERVAL = 1 # update interval in seconds
CONFIGFILE = "chamber.ini"

DEFAULT_TEMP = -999
DEFAULT_BUFFER_BEER_TEMP = 0.5       # +/- degrees celcius beer is from target when heating/cooling will be turned on
DEFAULT_BUFFER_CHAMBER_SCALE = 5.0   # scale factor of temperature delta chamber is from target controlling when heating/cooling will be turned on/off
DEFAULT_ON_DELAY = 600
TEMP_CHANGE_THRESHOLD = 5.0

PIN_HEAT_RELAY = 5 # motion pin
PIN_HEAT_LED = 23 # motion pin
PIN_COOL_RELAY = 6 # motion pin
PIN_COOL_LED = 24 # motion pin

class Chamber(threading.Thread):

    def __init__(self, _tilt):
        threading.Thread.__init__(self)

        # Set the GPIO naming conventions
        GPIO.setmode (GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(PIN_HEAT_RELAY, GPIO.OUT) # GPIO Assign mode
        GPIO.setup(PIN_HEAT_LED, GPIO.OUT) # GPIO Assign mode
        GPIO.setup(PIN_COOL_RELAY, GPIO.OUT) # GPIO Assign mode
        GPIO.setup(PIN_COOL_LED, GPIO.OUT) # GPIO Assign mode


        self.stopThread = True              # flag used for stopping the background thread
        self.tilt = _tilt
        self.tiltcolor = None
        self.tempDates = [datetime.datetime.now()]
        self.targetTemps = [DEFAULT_TEMP]
        self.targetTemp = DEFAULT_TEMP
        self.bufferBeerTemp = DEFAULT_BUFFER_BEER_TEMP
        self.bufferChamberScale = DEFAULT_BUFFER_CHAMBER_SCALE
        self.beerTemp = DEFAULT_TEMP
        self.beerWireTemp = DEFAULT_TEMP
        self.chamberTemp = DEFAULT_TEMP
        self.timeData = datetime.datetime.now()
        self.bTiltControlled = False

        self.onDelay = DEFAULT_ON_DELAY
        self.beerTAdjust = 0.0
        self.chamberTAdjust = 0.0

        self.coolEndTime = datetime.datetime.now() - datetime.timedelta(seconds=self.onDelay*2)
        self.heatEndTime = datetime.datetime.now() - datetime.timedelta(seconds=self.onDelay*2)

        self.bHeatOn = False
        self.bCoolOn = False
        self._controlheatingcooling(PIN_HEAT_RELAY, PIN_HEAT_LED, False)
        self._controlheatingcooling(PIN_COOL_RELAY, PIN_COOL_LED, False)
        
    def isHeating(self):
        return self.bHeatOn

    def isCooling(self):
        return self.bCoolOn

    # Starts the background thread
    def run(self):
        logger.info("Starting Chamber")
        self.stopThread = False
        
        while self.stopThread != True:
            self._readConf()
            self._evaluate()
            time.sleep(UPDATE_INVERVAL)

        self._controlheatingcooling(PIN_COOL_RELAY, PIN_COOL_LED, False)
        self._controlheatingcooling(PIN_HEAT_RELAY, PIN_HEAT_LED, False)
        logger.info("Chamber Stopped")


    def __del__(self):
        logger.debug("Delete chamber class")

    def stop(self):
        self.stopThread = True
    
    def _evaluate(self):
        logger.debug("_evaluate")
        self.targetTemps
        self.tempDates
        self.bufferBeerTemp
        self.bufferChamberScale

        # read latest temperatures
        self._readChamberTemp()
        self._readBeerTemp()

        _curTime = datetime.datetime.now()
            
        # check which of the temperature change dates have passed
        datesPassed = 0
        for dt in self.tempDates:
            if dt < _curTime:
                datesPassed = datesPassed + 1
        
        # No configured dates have passed, leave chamer powered off
        if datesPassed == 0:
            # Turn off heating and cooling
            logger.debug("Leaving chamber heating/cooling off until first date reached: " + self.tempDates[datesPassed].strftime("%d.%m.%Y %H:%M:%S"))
            self._controlheatingcooling(PIN_HEAT_RELAY, PIN_HEAT_LED, False)
            self._controlheatingcooling(PIN_COOL_RELAY, PIN_COOL_LED, False)
            return

        # check if last date has been reached. If so, heating/cooling should stop
        elif datesPassed == len(self.tempDates):
            logger.debug("Last date reached turning heating/cooling off: " + self.tempDates[datesPassed-1].strftime("%d.%m.%Y %H:%M:%S"))
            self._controlheatingcooling(PIN_HEAT_RELAY, PIN_HEAT_LED, False)
            self._controlheatingcooling(PIN_COOL_RELAY, PIN_COOL_LED, False)
            return

        # date is within configured range    
        else:
            self.targetTemp = self.targetTemps[datesPassed-1]

            # beer is warmer than target + buffer, consider cooling
            if self.beerTemp > (self.targetTemp + self.bufferBeerTemp):
                # check how much cooler chamber is compared to target, do not want it too low or beer temperature will overshoot too far.
                if (self.targetTemp - self.chamberTemp) < self.bufferChamberScale*(self.beerTemp - self.targetTemp):
                    # Turn cooling ON
                    logger.debug("Cooling to be turned ON - Target: " + str(self.targetTemp) + "; Beer: " + str(self.beerTemp) + "; Chamber: " + str(self.chamberTemp) + "; Beer Buffer: " + str(self.bufferBeerTemp) + "; Chamber Scale: " + str(self.bufferChamberScale))
                    self._controlheatingcooling(PIN_COOL_RELAY, PIN_COOL_LED, True)
                else:
                    logger.debug("Chamber is cold enough to cool beer")
                    self._controlheatingcooling(PIN_COOL_RELAY, PIN_COOL_LED, False)
                    self._controlheatingcooling(PIN_HEAT_RELAY, PIN_HEAT_LED, False)

            # beer is cooler than target + buffer, consider heating
            elif self.beerTemp < (self.targetTemp - self.bufferBeerTemp):
                # check how much hotter chamber is compared to target, do not want it too high or beer temperature will overshoot too far.
               if (self.chamberTemp - self.targetTemp) < self.bufferChamberScale*(self.targetTemp - self.beerTemp):
                    # Turn heating ON
                    logger.debug("Heating to be turned ON - Target: " + str(self.targetTemp) + "; Beer: " + str(self.beerTemp) + "; Chamber: " + str(self.chamberTemp) + "; Beer Buffer: " + str(self.bufferBeerTemp) + "; Chamber Scale: " + str(self.bufferChamberScale))
                    self._controlheatingcooling(PIN_HEAT_RELAY, PIN_HEAT_LED, True)
               else:
                    logger.debug("Chamber is warm enough to heat beer")
                    self._controlheatingcooling(PIN_COOL_RELAY, PIN_COOL_LED, False)
                    self._controlheatingcooling(PIN_HEAT_RELAY, PIN_HEAT_LED, False)

            # beer is within range of target +/- buffer
            else:
                logger.debug("No heating/cooling needed - Target: " + str(self.targetTemp) + "; Beer: " + str(self.beerTemp) + "; Chamber: " + str(self.chamberTemp) + "; Beer Buffer: " + str(self.bufferBeerTemp) + "; Chamber Scale: " + str(self.bufferChamberScale))
                self._controlheatingcooling(PIN_COOL_RELAY, PIN_COOL_LED, False)
                self._controlheatingcooling(PIN_HEAT_RELAY, PIN_HEAT_LED, False)


    def getDates(self):
        return self.tempDates.copy()

    def getTemps(self):
        return self.targetTemps.copy()

    def getTargetTemp(self):
        if self.targetTemp == DEFAULT_TEMP:
            return None
        else:
            return self.targetTemp

    def getBeerTemp(self):
        if self.beerTemp != DEFAULT_TEMP:
            return self.beerTemp

        return None

    def getWiredBeerTemp(self):
        if self.beerWireTemp != DEFAULT_TEMP:
            return self.beerWireTemp
        return None

    def getChamberTemp(self):
        if self.chamberTemp != DEFAULT_TEMP:
            return self.chamberTemp
        return None

    # reads beer temperature from tilt, if configured and less than 5min old, or wire and returns value
    def _readBeerTemp(self):
        logger.debug("getBeerTemp")

        _tiltdata = {}

        # if Tilt is configured and available replace related values
        if (self.tilt is not None and self.tiltcolor is not None):
            _tiltdata = self.tilt.getData(self.tiltcolor)

            if _tiltdata is not None:
                _tiltdatatime = _tiltdata[tilt.TIME]
            
                if _tiltdatatime is not None and _tiltdatatime > datetime.datetime.now() - datetime.timedelta(minutes=5):
                    _beerTemp = _tiltdata[tilt.TEMP]
                    if _beerTemp is not None:
                        self.beerTemp = _beerTemp
                        self.bTiltControlled = True

                        if self.timeData < _tiltdatatime:
                            self.timeData = _tiltdatatime
                    else:
                        logger.warning("Temp for "+self.tiltcolor+" tilt is None; using wired temperatures")
                        self.beerTemp = self._readWireBeerTemp()
                        self.bTiltControlled = False

                else:
                    logger.warning("Data for "+self.tiltcolor+" tilt is outdated; using wired temperatures")
                    self.beerTemp = self._readWireBeerTemp()
                    self.bTiltControlled = False
            else:
                logger.warning("Data for "+self.tiltcolor+" tilt unavailable; using wired temperatures")
                self.beerTemp = self._readWireBeerTemp()
                self.bTiltControlled = False
        # Tilt is not configured or color is not specified
        else:
           self.beerTemp = self._readWireBeerTemp()
           self.bTiltControlled = False

        if self.beerTemp == DEFAULT_TEMP:
            self.bTiltControlled = False
            return None
        else:
            return self.beerTemp
    
    def _readWireBeerTemp(self):
        logger.debug("getWireBeerTemp")

        id = '28-02148151b0ff'

        _temp = self._readTemp(id) + self.beerTAdjust
        
        # if the stored temperature is default value or less than change threshold with updated reading, store new value
        if self.beerWireTemp == DEFAULT_TEMP or abs(_temp - self.beerWireTemp) < TEMP_CHANGE_THRESHOLD:
            self.beerWireTemp = _temp
        # bigger jump in temperature threshold, take average of 10 readings
        else:
            self.beerWireTemp = self._avgTemp(id,10) + self.beerTAdjust

        if self.beerWireTemp == DEFAULT_TEMP:
            return None
        else:
            return self.beerWireTemp

    def _readChamberTemp(self):
        logger.debug("getChamberTemp")
        
        id = '28-0417004ebfff'

        _temp = self._readTemp(id) + self.chamberTAdjust
        
        # if the stored temperature is default value or less than change threshold with updated reading, store new value
        if self.chamberTemp == DEFAULT_TEMP or abs(_temp - self.chamberTemp) < TEMP_CHANGE_THRESHOLD:
            self.chamberTemp = _temp
        # bigger jump in temperature threshold, take average of 10 readings
        else:
            self.chamberTemp = self._avgTemp(id,10) + self.chamberTAdjust

        if self.chamberTemp == DEFAULT_TEMP:
            return None
        else:
            return self.chamberTemp

    def isTiltControlled(self):
        return self.bTiltControlled


    def setTiltColor(self, _color):
        if tilt.validColor(_color):
            self.tiltcolor = _color
        else:
            self.tiltcolor = None

    # returns time when data was updated
    def timeOfData(self):
        return self.timeData

    def _controlheatingcooling(self, _relay, _led, _bool):
        logger.debug("_controlheatingcooling")

        curTime = datetime.datetime.now()
        sTime = curTime.strftime("%d.%m.%Y %H:%M:%S")

        if _relay == PIN_HEAT_RELAY and self.bHeatOn == True and _bool == False:
            self.heatEndTime = curTime
            self.bHeatOn = False

        elif _relay == PIN_HEAT_RELAY and self.bHeatOn == False and _bool == True:
            self._controlheatingcooling(PIN_COOL_RELAY, PIN_COOL_LED, False)

            if curTime < self.heatEndTime + datetime.timedelta(seconds=self.onDelay):
                logger.debug("("+sTime+"): on delay has not expired: "+(self.heatEndTime + datetime.timedelta(seconds=self.onDelay)).strftime("%d.%m.%Y %H:%M:%S"))
                return

            self.bHeatOn = True 
        
        elif _relay == PIN_COOL_RELAY and self.bCoolOn == True and _bool == False:
            self.coolEndTime = curTime
            self.bCoolOn = False

        elif _relay == PIN_COOL_RELAY and self.bCoolOn == False and _bool == True:
            self._controlheatingcooling(PIN_HEAT_RELAY, PIN_HEAT_LED, False)

            if curTime < self.coolEndTime + datetime.timedelta(seconds=self.onDelay):
                logger.debug("("+sTime+"): on delay has not expired: "+(self.coolEndTime + datetime.timedelta(seconds=self.onDelay)).strftime("%d.%m.%Y %H:%M:%S"))
                return

            self.bCoolOn = True

        if _bool:
            logger.debug("("+sTime+"): Turn ON relay: "+str(_relay))
            GPIO.output(_relay, GPIO.LOW) # Turn relay ON
            GPIO.output(_led, GPIO.HIGH) # Turn led ON
        else:
            logger.debug("("+sTime+"): Turn relay OFF: "+str(_relay))
            GPIO.output(_relay, GPIO.HIGH) # Turn relay OFF
            GPIO.output(_led, GPIO.LOW) # Turn led OFF

    def _avgTemp(self, id, _num):
        logger.debug("_avgtemp")

        interval = 0
        _temp = 0.0

        for i in range (0, _num):
            t = self._readTemp(id)
            if t != DEFAULT_TEMP:
                _temp += t
                interval += 1

        logger.debug("_avgtemp: "+(str)(_temp/interval))
        return _temp/interval


    def _readTemp(self, id):
        logger.debug("_gettemp")
        try:
            mytemp = ''
            filename = 'w1_slave'
            f = open('/sys/bus/w1/devices/' + id + '/' + filename, 'r')
            line = f.readline() # read 1st line
            crc = line.rsplit(' ',1)
            crc = crc[1].replace('\n', '')
            if crc=='YES':
                line = f.readline() # read 2nd line
                mytemp = line.rsplit('t=',1)
            else:
                mytemp = DEFAULT_TEMP
            f.close()
            
            self.timeData = datetime.datetime.now()

            _temp = (float)(mytemp[1])/1000

            logger.debug("_gettemp: "+(str)(_temp))

            return _temp

        except:
            return DEFAULT_TEMP

    # Read class parameters from configuration ini file.
    # Format:
    # [Chamber]
    # MessageLevel = INFO
    # Temps = 18,21,0
    # Dates = 26/03/2019 12:00:00,28/09/2019 13:00:00,14/10/2019 14:00:00,20/04/2020 14:00:00
    # BeerTemperatureBuffer = 0.2
    # ChamberScaleBuffer = 5.0    
    def _readConf(self):

        try:
            if os.path.isfile(CONFIGFILE) == False:
                logger.error("Chamber configuration file is not valid: "+CONFIGFILE)

            ini = configparser.ConfigParser()
            ini.read(CONFIGFILE)

            if 'Chamber' in ini:
                logger.debug("Reading Chamber config")
        
                config = ini['Chamber']
                
                try:
                    if config["MessageLevel"] == "DEBUG":
                        logger.setLevel(logging.DEBUG)
                    elif config["MessageLevel"] == "WARNING":
                        logger.setLevel(logging.WARNING)
                    elif config["MessageLevel"] == "ERROR":
                        logger.setLevel(logging.ERROR)
                    elif config["MessageLevel"] == "INFO":
                        logger.setLevel(logging.INFO)
                    else:
                        logger.setLevel(logging.INFO)
                except KeyError:
                    logger.setLevel(logging.INFO)
                                    
                # Read temperatures to target for each date
                try:
                    if config["Temps"] != "":
                        self.targetTemps = []
                        t = config["Temps"].split(",")
                        for x in t:
                            self.targetTemps.append(float(x))
                    else:
                        raise Exception
                except:
                    self.targetTemps = [DEFAULT_TEMP]
                    logger.warning("Invalid temp values; using default: "+str(self.targetTemps[0]))

                # Read dates when temperature should change
                try:
                    if config["Dates"] != "":
                        self.tempDates = []
                        dts = config["Dates"].split(",")
                        for x in dts:
                            self.tempDates.append(datetime.datetime.strptime(x, '%d/%m/%Y %H:%M:%S'))
                    else:
                        raise Exception
                except:
                    self.tempDates = [datetime.datetime.now(),datetime.datetime.now()]
                    logger.warning("Invalid date values; using default. Heating/cooling will NOT start")

        
                if len(self.tempDates) != len(self.targetTemps)+1:
                    self.tempDates = [datetime.datetime.now(),datetime.datetime.now()]
                    self.targetTemps = [DEFAULT_TEMP]
                    logger.warning("Invalid date or time values; using default. Heating/cooling will NOT start")


                try:
                    if config["BeerTemperatureBuffer"] != "" and float(config["BeerTemperatureBuffer"]) >= 0.0:
                        self.bufferBeerTemp = float(config.get("BeerTemperatureBuffer"))
                    else:
                        raise Exception
                except:
                    self.bufferBeerTemp = DEFAULT_BUFFER_BEER_TEMP
                    logger.warning("Invalid beer temperature buffer in configuration; using default: "+str(self.bufferBeerTemp))

                try:
                    if config["ChamberScaleBuffer"] != "" and float(config["ChamberScaleBuffer"]) >= 0.0:
                            self.bufferChamberScale = float(config.get("ChamberScaleBuffer"))
                    else:
                        raise Exception
                except:
                    self.bufferChamberScale = DEFAULT_BUFFER_CHAMBER_SCALE
                    logger.warning("Invalid chamber scale buffer in configuration; using default: "+str(self.bufferChamberScale))

                try:
                    if config["BeerTempAdjust"] != "":
                        self.beerTAdjust = float(config.get("BeerTempAdjust"))
                    else:
                        raise Exception
                except:
                    self.beerTAdjust = 0.0
                    logger.warning("Invalid BeerTempAdjust in configuration; using default: "+str(self.beerTAdjust))

                try:
                    if config["ChamberTempAdjust"] != "":
                        self.chamberTAdjust = float(config.get("ChamberTempAdjust"))
                    else:
                        raise Exception
                except:
                    self.chamberTAdjust = 0.0
                    logger.warning("Invalid ChamberTempAdjust in configuration; using default: "+str(self.chamberTAdjust))

                try:
                    if config["OnDelay"] != "" and int(config["OnDelay"]) >= 0:
                        self.onDelay = int(config.get("OnDelay"))*60
                    else:
                        raise Exception
                except:
                    self.onDelay = DEFAULT_ON_DELAY
                    logger.warning("Invalid OnDelay in configuration; using default: "+str(self.onDelay)+" seconds")

        except:
            logger.warning("Problem read from configuration file: "+CONFIGFILE)
       
            
        logger.debug("Chamber config updated")

