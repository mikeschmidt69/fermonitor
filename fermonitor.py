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
import configparser
import threading
import logging
from logging.handlers import TimedRotatingFileHandler
from distutils.util import strtobool
from flask import Flask, render_template                                                         
from influxdb import InfluxDBClient

import chamber
import interface
import tilt
import brewfather

CONFIGFILE = "fermonitor.ini"

CONTROL_TILT = 0
CONTROL_WIRE = 1

cTilt = None
cChamber = None
cBrewfather = None

def read_settings():
    global sTiltColor
    global chamberControlTemp
    global logLevel

    sTiltColor = None
    chamberControlTemp = CONTROL_WIRE
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
        sTiltColor = None

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
    
    global cTilt
    global cChamber
    global cBrewfather
    
    logger.info("Starting Fermonitor...")

    read_settings()

    cInterface = interface.Interface("Fermonitor......")
    cInterface.setLogLevel(logLevel)
    cInterface.start()

    cTilt = tilt.Tilt()
    cTilt.start()

    cChamber = chamber.Chamber(cTilt)
    cChamber.start()

    # Start BrewFather thread to store temp and gravity
    logger.debug("Starting BrewFather Thread")
    cBrewfather = brewfather.BrewFather()
    cBrewfather.start()

    client = InfluxDBClient(host='localhost', port=8086)
    client.create_database('brewing')
    client.switch_database('brewing')

    # Main loop for reading and logging data as well as controllng fermentor
    while True:

        read_settings()
        cInterface.setLogLevel(logLevel)

        if chamberControlTemp == CONTROL_TILT and sTiltColor is not None:
            cChamber.setTiltColor(sTiltColor)
        else:
            cChamber.setTiltColor(None)

        _tBeerT = None
        _tBeerSG = None
        _cBeerT = cChamber.getBeerTemp()
        _cWireBeerT = cChamber.getWiredBeerTemp()
        _cChamberT = cChamber.getChamberTemp()
        _cTargetT = cChamber.getTargetTemp()
        _cTiltControlled = cChamber.isTiltControlled()
        _cHeating = cChamber.isHeating()
        _cCooling = cChamber.isCooling()
        _cTimeData = cChamber.timeOfData()

        if sTiltColor is not None:
            _tiltdata = {}
            _tiltdata = cTilt.getData(sTiltColor)
            if _tiltdata is not None:
                _tBeerSG = _tiltdata.get(tilt.SG)

        cBrewfather.setData(_cBeerT, _cChamberT, _tBeerSG)        

        cInterface.setData( \
            _cTargetT, \
            _cWireBeerT, \
            _cChamberT, \
            _tBeerSG, \
            _tBeerT, \
            _cTiltControlled)

        _fields = {}

        if _cTargetT is not None:
            _fields["targetTemp"] = str(round(float(_cTargetT),1))
        if _cChamberT is not None:
            _fields["chamberTemp"] = str(round(float(_cChamberT),1))
        if _cBeerT is not None:
            _fields["beerTemp"] = str(round(float(_cWireBeerT),1))
        if _tBeerT is not None:
            _fields["tiltTemp"] = str(round(float(_tBeerT),1))
        if _tBeerSG is not None:
            _fields["gravity"] = "{:5.3f}".format(round(float(_tBeerSG),3))
        _fields["heating"] = _cHeating
        _fields["cooling"] = _cCooling
        _fields["tiltControlled"] = _cTiltControlled

        _postdata = [
            {
                "measurement": "fermonitor",
                "time": datetime.datetime.utcnow(),
                "fields": _fields
            }
        ]
      
        client.write_points(_postdata)

        time.sleep(0.5)

app = Flask(__name__)
@app.route("/", methods=["GET","POST"])
def index_html():
    _data = {}

    if cChamber is not None:
        _data['dates'] = ', '.join([item.strftime("%d.%m.%Y %H:%M:%S") for item in cChamber.getDates()])
        _data['temps'] = ', '.join([str(round(float(item),1)) for item in cChamber.getTemps()])
        if cChamber.getTargetTemp() is not None:
            _data['target'] = str(round(float(cChamber.getTargetTemp()),1))
        if cChamber.getBeerTemp() is not None:
            _data['tempBeer'] = str(round(float(cChamber.getBeerTemp()),1))
        if cChamber.getWiredBeerTemp() is not None:
            _data['tempBeerWire'] = str(round(float(cChamber.getWiredBeerTemp()),1))
        if cChamber.getChamberTemp() is not None:
            _data['tempChamber'] = str(round(float(cChamber.getChamberTemp()),1))
        if cChamber.timeOfData() is not None:
            _data['timeBeer'] = cChamber.timeOfData().strftime("%d.%m.%Y %H:%M:%S")
        if cChamber.isTiltControlled() and sTiltColor is not None:
            _data['tiltColor'] = sTiltColor
        _data['heating'] = str(cChamber.isHeating())
        _data['cooling'] = str(cChamber.isCooling())

    return render_template('chamber.html', data=_data)

@app.route("/tilt", methods=["GET","POST"])
def tilt_html():
    _data = []
    if sTiltColor is not None:
        _data = cTilt.getAllData().values()

    return render_template('tilt.html', data=_data)

@app.route("/brewfather", methods=["GET","POST"])
def brewfather_html():
    _nextdata = ""
    _lastdata = ""
    _timeData = ""

    if cBrewfather is not None:
        _lastdata = cBrewfather.getLastJSON()
        _nextdata = cBrewfather.getNextJSON()
        _timeData = cBrewfather.getLastRequestTime().strftime("%d.%m.%Y %H:%M:%S")

    return render_template('brewfather.html', lastdata=_lastdata, nextdata=_nextdata, timeData=_timeData)


if __name__ == "__main__": #dont run this as a module

    try:
        LOGFILE = "fermonitor.log"
        logging.basicConfig(format='%(asctime)s %(levelname)s {%(module)s} [%(funcName)s] %(message)s',datefmt='%Y-%m-%d,%H:%M:%S', level=logging.INFO)
        logger = logging.getLogger('FERMONITOR')
        logger.setLevel(logging.INFO)
        handler = TimedRotatingFileHandler(LOGFILE, when="h", interval=24, backupCount=21)
        formatter = logging.Formatter('%(asctime)s %(levelname)s {%(module)s} [%(funcName)s] %(message)s', datefmt='%Y-%m-%d,%H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        threading.Thread(target=app.run, args=('0.0.0.0','5000',False)).start()
        main()

    except KeyboardInterrupt:
        if cTilt is not None:
            cTilt.stop()
            cTilt = None
        if cChamber is not None:
            cChamber.stop()
            cChamber = None
        if cBrewfather is not None:
            cBrewfather.stop()
            cBrewfather = None

        print("...Fermonitor Stopped")
 
