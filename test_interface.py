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

# import sys
# import datetime
# import time
# import os
import random
import logging
from setup_logger import logger
# from distutils.util import strtobool

import interface

logger = logging.getLogger('TEST_INTERFACE')
logger.setLevel(logging.INFO)


################################################################
def main():

    ui = interface.Interface("Test Interface")
    ui.setLogLevel(logging.DEBUG)  
    ui.start()

    for x in range(1000):
    
        Tsg = random.randint(1,101)/100 * 1.2

        TbeerT = random.randint(1,101)/100 * 25

        if random.randint(1,3) > 1:
            TbeerT = -TbeerT

        WchamberT = random.randint(1,101)/100 * 25

        if random.randint(1,3) > 1:
            WchamberT = -WchamberT

        ui.setData(21, TbeerT, Tsg, TbeerT*1.3, WchamberT)
        time.sleep(1)

    ui.stop()


if __name__ == "__main__": #dont run this as a module

    try:
        main()

    except KeyboardInterrupt:
        interface = None
        print("...Interface Test Stopped")
 
    
