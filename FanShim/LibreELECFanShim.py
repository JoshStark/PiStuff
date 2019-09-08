#!/usr/bin/env python

# =============
# Heavily influenced by (and some code taken from) the official Pimoroni fanshim-python
# libraries: https://github.com/pimoroni/fanshim-python
# 
# The idea to produce this was also borne from Phil Randal's blog post regarding LibreELEC:
# http://www.philrandal.co.uk/blog/archives/2019/07/entry_214.html
#
# =============
# MIT License
#
# Copyright (c) 2019 Josh Stark.
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
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

import os
import time
import signal
import subprocess
import argparse
import atexit

import logging

LOG_HANDLER = logging.StreamHandler()
LOG_HANDLER.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

LOG = logging.getLogger('LibreELECFanShim')
LOG.addHandler(LOG_HANDLER)
LOG.setLevel(logging.ERROR)

import sys
sys.path.append('/storage/.kodi/addons/virtual.rpi-tools/lib')

import RPi.GPIO as GPIO

class LibreELECFanShim():

    def __init__(self, pin_fancontrol=18):
        """
        A customised definition for the Fan Shim taking into account
        the semi-limited libraries made available via LibreELEC
        """

        self._pin_fancontrol = pin_fancontrol

        atexit.register(self._cleanup)

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._pin_fancontrol, GPIO.OUT)

        # Initially turn off the fan
        self.set_fan_off()

    def get_fan(self):
        """Get current fan state."""
        return GPIO.input(self._pin_fancontrol)

    def toggle_fan(self):
        """Toggle fan state."""
        return self.set_fan(False if self._get_fan() else True)

    def set_fan(self, fan_state):
        """
        Set the fan on/off.
        :param fan_state: True/False for on/off
        """
        GPIO.output(self._pin_fancontrol, True if fan_state else False)
        return True if fan_state else False

    def set_fan_on(self):
        """
        Convenience function to start fan
        """
        self.set_fan(True)

    def set_fan_off(self):
        """
        Convenience function to stop fan
        """
        self.set_fan(False)

    def _cleanup(self):
        """
        Cleans up GPIO and turns off the fan.
        """
        self.set_fan_off()
        GPIO.cleanup()

class FanShimMonitor():

    def __init__(self, fanshim, threshold_off=45.0, threshold_on=65.0, interval=5, verbose=False):
        """
        Runnable class which controls a fan instance
        
        :param threshold_off: The minimum temperature the CPU must hit before the fan turns off
        :param threshold_on:  The minimum temperature the CPU must hit before the fan turns on
        """

        if None == fanshim:
            raise Exception("fanshim must not be None")

        self._fanshim       = fanshim
        self._threshold_off = threshold_off
        self._threshold_on  = threshold_on
        self._interval      = interval
        self._fan_running   = False

        if verbose:
            LOG.setLevel(logging.DEBUG)

    @staticmethod
    def _get_cpu_temp():
        
        temp = subprocess.check_output([ 'vcgencmd', 'measure_temp' ])[5:-3]
        return float(temp)

    def monitor_fan(self):
        """
        Checks the CPU's current temperature and makes a decision whether or not
        to enable the fan. This takes into account both thresholds and the
        current running state of the fan.
        """
        
        while True:
        
            current_cpu_temp = self._get_cpu_temp()
            LOG.info("Current Temp: {:05.02f}, Fan Running: {}".format(current_cpu_temp, self._fan_running))

            if current_cpu_temp >= self._threshold_on and not self._fan_running:
                
                LOG.info("Temp has hit upper threshold of {} while turned off. Turning fan on.".format(self._threshold_on))
                self._fan_running = True
                self._fanshim.set_fan_on()

            elif current_cpu_temp <= self._threshold_off and self._fan_running:

                LOG.info("Temp has hit lower threshold of {} while turned on. Turning fan off.".format(self._threshold_off))
                self._fan_running = False
                self._fanshim.set_fan_off()

            time.sleep(self._interval)

def run(controller):

    try:
        controller.monitor_fan()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--off-threshold', type=float,          default=45.0,  help='The minimum temperature the CPU must hit before the fan turns off')
    parser.add_argument('--on-threshold',  type=float,          default=65.0,  help='The minimum temperature the CPU must hit before the fan turns on')
    parser.add_argument('--interval',      type=float,          default=5.0,   help='Delay, in seconds, between temperature readings')
    parser.add_argument('--verbose',       action='store_true', default=False, help='Output temp and fan status messages')

    args = parser.parse_args()

    fanshim    = LibreELECFanShim()
    controller = FanShimMonitor(fanshim, args.off_threshold, args.on_threshold, args.interval, args.verbose) 

    run(controller)
