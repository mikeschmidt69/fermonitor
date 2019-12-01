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
import logging
from setup_logger import logger
from distutils.util import strtobool

import controller
import chamber

logger = logging.getLogger('TEST_CHAMBER')
logger.setLevel(logging.INFO)

control = controller.Controller()
fridge = chamber.Chamber(control, None)

################################################################
def main():
    
    control.setLogLevel(logging.DEBUG)      
    fridge.setLogLevel(logging.DEBUG)      

    control.setDelay(30)
    control.start()

    curTime = datetime.datetime.now()

    dates = [curTime + datetime.timedelta(seconds=10), curTime + datetime.timedelta(seconds=20), curTime + datetime.timedelta(seconds=40), curTime + datetime.timedelta(seconds=70), curTime + datetime.timedelta(seconds=100)]
    temps = [100,1,50,5]

    fridge.setControlTemps(temps, dates, 1, 5)
    fridge.start()

    time.sleep(120)

    control.stop()
    fridge.stop()


if __name__ == "__main__": #dont run this as a module

    try:
        main()

    except KeyboardInterrupt:
        control = None
        fridge = None
        print("...Chamber Test Stopped")
 
    
