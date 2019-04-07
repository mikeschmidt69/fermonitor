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
import glob
import time
import os
import threading
import logging
from setup_logger import logger
import configparser

logger = logging.getLogger('onewiretemp')
logger.setLevel(logging.INFO)

# Initialize the GPIO Pins
os.system('modprobe w1-gpio') # Turns on the GPIO module
os.system('modprobe w1-therm') # Truns on the Temperature module

# Finds the correct device file that holds the temperature data
base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'

MINIMUM_INVERVAL = 10 # minimum update interval in seconds

class OneWireTemp (threading.Thread):

    # Constructor for class
    def __init__(self, _configFile):
        threading.Thread.__init__(self)
    
        if os.path.isfile(_configFile) == False:
            raise IOError("OneWireTemp configuration file is not valid: "+_configFile)

        self.configFile = _configFile
        self.interval = MINIMUM_INVERVAL # interval in seconds the sensor should be read

        self.lastUpdateTime = datetime.datetime.now() - datetime.timedelta(seconds=self.interval) # last time the sensor was read
     
        self.temp = -273.15 # last read temperature from tilt
        self.validData = False
        self.useOneWireTemp = True
        self._readdata()
    
        self.stopThread = True
    

    # Starts background thread that updates the data from Tilt hydrometer (temp, specific gravity) on regular basis.
    # This is not a realtime operation so thread sleeps for 5s after each iteration
    def run(self):
        logger.info("Starting OneWireTemp monitoring.")
        self.stopThread = False
        while self.stopThread != True:
            self._readConf(self.configFile)
            self._update()    # calls method that updates data from sensor if update time interval has lapsed
            time.sleep(MINIMUM_INVERVAL)
        logger.info("OneWireTemp Monitoring Stopped.")


    # Returns last read temperature reading from Tilt
    def getTemp(self):
        return self.temp


    # returns True/False if data is valid. Data is not valid until read from the actual Tilt device
    def isDataValid(self):
        return self.validData   


    # returns time when date and specific gravity were updated from Tilt
    def timeOfData(self):
        return self.lastUpdateTime


    # stops the background thread updating data coming from configured Tilt
    def stop(self):
        self.stopThread = True


    def _readConf(self,configFile):
            
        if os.path.isfile(configFile) == False:
            logger.error("OneWireTemp configuration file is not valid: "+configFile)
        else:
            ini = configparser.ConfigParser()

            logger.debug("Reading OneWireTemp config: " + configFile)
            ini.read(configFile)

            if 'OneWireTemp' in ini:
                config = ini['OneWireTemp']

                try:
                    if config["UpdateIntervalSeconds"] != "" and int(config["UpdateIntervalSeconds"]) >= MINIMUM_INVERVAL:
                        self.interval = int(config.get("UpdateIntervalSeconds"))
                    else:
                        self.interval = MINIMUM_INVERVAL
                except KeyError:
                    self.interval = MINIMUM_INVERVAL
                
                try:
                    if config["MessageLevel"] == "DEBUG":
                        logger.setLevel(logging.DEBUG)
                    elif config["MessageLevel"] == "WARNING":
                        logger.setLevel(logging.ERROR)
                    elif config["MessageLevel"] == "ERROR":
                        logger.setLevel(logging.WARNING)
                    elif config["MessageLevel"] == "INFO":
                        logger.setLevel(logging.INFO)
                    else:
                        logger.setLevel(logging.INFO)
                except KeyError:
                    logger.setLevel(logging.INFO)

            else:
                logger.error("[OneWireTemp] section not found in ini file: " + configFile)
                self.interval = MINIMUM_INVERVAL
        logger.debug("Done reading OneWireTemp config.")
                        
 
    # Internal method for checking if the update time interval has lapsed and new data should be read from Tilt
    def _update(self):
        updateTime = self.lastUpdateTime + datetime.timedelta(seconds=self.interval)
        if datetime.datetime.now() > updateTime:
            logger.debug("Update data")
            self._readdata()
        else:
            logger.debug("Update interval not reached:"+datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S") +" / "+ updateTime.strftime("%d.%m.%Y %H:%M:%S")) 


    # A function that reads the sensors data
    def _read_temp_raw(self):
        lines = ""
        try:
            f = open(device_file, 'r') # Opens the temperature device file
            lines = f.readlines() # Returns the text
            f.close()
        except:
            if self.validData:
                logger.warning("Error reading from OneWireTemp sensor.")
            self.validData = False
            lines = ""
        return lines

    # convert the value of the sensor into temperature
    def _readdata(self):
        lines = self._read_temp_raw() # read the temperature device file

        # while the first line does not contain 'YES', wait for 0.2s
        # and then read the device file again.
        retries = 50
        while lines[0].strip()[-3:] != 'YES' and retries > 0:
            time.sleep(0.2)
            lines = self._read_temp_raw()
            retries = retries - 1
        
        if retries <= 0:
            self.validData = False

        else:    
            # Look for th eposition of the '=' in the second line of the
            # device file
            equals_pos = lines[1].find('t=')

            # If the '=' is found, convert the rest of th eline after the
            # '=' into degrees Celsius
            if equals_pos != -1:
                temp_string = lines[1][equals_pos+2:]
                self.temp = float(temp_string) / 1000.0
                if self.validData == False:
                    logger.info("OneWireTemp sensor reading active.")
                self.validData = True
                self.lastUpdateTime = datetime.datetime.now()
                logger.info("Updated OneWireTemp: "+str(self.temp) + "C")
