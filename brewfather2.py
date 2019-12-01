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

from urllib import request, parse
import json
import requests
import datetime
import time
import threading
import logging
from setup_logger import logger

logger = logging.getLogger('BREWFATHER')
logger.setLevel(logging.INFO)

MINIMUM_INTERVAL = 900 # minimum number of seconds the BrewFather.app can be updated (i.e. 15min)

# Brewfather class used for passing brew related logging data to BrewFather.app so it can be displayed for batch connected in the app.
class BrewFather (threading.Thread):

    # Constructor
    def __init__(self, _name, _url, _interval):
        threading.Thread.__init__(self)
    
        self.sName = _name
        self.sURL = _url                    # custom URL provided in the BrewFather app where data should be sent in JSON format
        if _interval > MINIMUM_INTERVAL:    # interval in seconds for updating BrewFather; BrewFather rejects updates more often than 15min
            self.interval = _interval  
        else:
            self.interval = MINIMUM_INTERVAL

        self.stopThread = True              # flag used for stopping the background thread that updates BrewFather
        self.dataTime = datetime.datetime.now()

        # Data accepted by BrewFather; OK if some values are ""; not sure what happens if fields are missing.
        self.postdata = {
            "name": self.sName,
            "temp": "",
            "aux_temp": "", # Fridge Temp
            "ext_temp": "", # Room Temp
            "temp_unit": "C", # C, F, K
            "gravity": "",
            "gravity_unit": "G", # G, P
            "pressure": "",
            "pressure_unit": "BAR", # PSI, BAR, KPA
            "ph": "",
            "comment": "",
            "beer": ""
        }

        # Keeps track of last time BrewFather was updated to know when it can be updated again
        self.lastUpdateTime = datetime.datetime.now() - datetime.timedelta(seconds=self.interval) # last time the tilt was read
     

    # Starts the background thread for updating BrewFather with lastest data. First re-reads configuration file to check
    # if any of the settings have changed
    def run(self):
        logger.info("Starting BrewFather Logging: "+self.sName)
        self.stopThread = False
        while self.stopThread != True:
            self._update() 
            time.sleep(60)
        logger.info("BrewFather Monitoring Stopped: "+self.sName)


    # stops the background thread updating data coming from configured Tilt
    def stop(self):
        self.stopThread = True


    # set interval for updating Brewfather.app. Value in seconds (minimum value 900s)
    def setUpdateInterval(self, _interval):
        if _interval > MINIMUM_INTERVAL:
            self.interval = _interval
            logger.info(self.sName+": update interval: "+str(self.interval)+"s")


    # set logging level DEBUG, WARNING, ERROR, INFO. Default level is logging.INFO
    def setLoggingLevel(self, _logLevel):
        if _logLevel == logging.DEBUG:
            logger.setLevel(logging.DEBUG)
        elif _logLevel == logging.WARNING:
            logger.setLevel(logging.WARNING)
        elif _logLevel == logging.ERROR:
            logger.setLevel(logging.ERROR)
        else:
            logger.setLevel(logging.INFO)

    # sets the data currently supported by my system, will expand with system
    def setData(self, _beer_temp, _aux_temp, _gravity, _dataTime):
        if _beer_temp != None:
            self.postdata["temp"] = str(round(float(_beer_temp),1))
        if _aux_temp != None:
            self.postdata["aux_temp"] = str(round(float(_aux_temp),1))
        if _gravity != None:
            self.postdata["gravity"] = "{:5.3f}".format(round(float(_gravity),3))
        if _dataTime != None:
            self.dataTime = _dataTime

    # method for connecting and updating BrewFather.app
    def _update(self):
        updateTime = self.lastUpdateTime + datetime.timedelta(seconds=self.interval)

        # check Brewfather URL is defined
        # check the updated interval has elapsed since last update
        # check relevant data for the system is valid
        # check the data has been updated since last update
        if self.sURL != "" and datetime.datetime.now() > updateTime and \
            self.postdata["name"] != "" and self.dataTime > self.lastUpdateTime:
            
            params = json.dumps(self.postdata).encode('utf8')
            req = request.Request(self.sURL, data=params, headers={'content-type': 'application/json'})
            response = request.urlopen(req)
            logger.info("BrewFather: " + self.postdata["temp"] +"C, " + self.postdata["gravity"] + "SG, " + self.postdata["aux_temp"] +"C, " + datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
            self.lastUpdateTime = datetime.datetime.now()

        else:
            logger.debug("Update paramters:\nsUrl = "+self.sURL+"\npostdata.Name = "+self.postdata["name"] + \
                "\npostdata.temp = "+self.postdata["temp"]+"\npostdata.gravity = "+self.postdata["gravity"] + "\npostdata.aux_temp = "+self.postdata["aux_temp"] + \
                    "\ndataTime = "+self.dataTime.strftime("%d.%m.%Y %H:%M:%S") + \
                        "\nupdateTime = "+updateTime.strftime("%d.%m.%Y %H:%M:%S") + \
                            "\nlastUpdateTime = "+self.lastUpdateTime.strftime("%d.%m.%Y %H:%M:%S") + \
                               "\nCurrent Time = "+datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
