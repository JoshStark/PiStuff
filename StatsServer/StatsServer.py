#!/usr/bin/env python
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

import argparse
import time
import subprocess
import json

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

class PiStats:

    def __init__(self):
        """
        Gathering class which obtains metrics from the Raspberry Pi
        """

        self._previous_cpu_raw = {
            'idle': {
                'overall': 0,
                'core0': 0,
                'core1': 0,
                'core2': 0,
                'core3': 0
            },
            'total': {
                'overall': 0,
                'core0': 0,
                'core1': 0,
                'core2': 0,
                'core3': 0
            }
        }

    def get_network_bytes(self):
        """
        Returns the currently recorded number of bytes (in and out) over
        each of the device's registered network interfaces. This method
        will return a dict keyed on the interface:

        {
            'net_eth0' : {
                'tx': 8756734,
                'rx': 254363983
            },
            ...
        }
        """

        ifaces = {}

        interfaces_available = subprocess.check_output([ "ls", "/sys/class/net" ]).split()
        for iface in interfaces_available:

            rx = long(subprocess.check_output([ "cat", "/sys/class/net/{}/statistics/rx_bytes".format(iface) ]))
            tx = long(subprocess.check_output([ "cat", "/sys/class/net/{}/statistics/tx_bytes".format(iface) ]))

            ifaces["net_{}".format(iface)] = { 'tx': tx, 'rx': rx}

        return ifaces

    def get_mem_usage(self):
        """
        Calculates various memory statistics. Calculations taken from: https://stackoverflow.com/a/41251290
        Unlike some commands such as 'free' which may or may not include buffers
        and cache in the mem_used value, this always omits it.
        """

        mem_total       = 0
        mem_cached      = 0
        mem_buffered    = 0
        mem_free        = 0
        mem_reclaimable = 0
        mem_shmem       = 0

        meminfo = subprocess.check_output([ "cat", "/proc/meminfo" ]).splitlines()
        for line in meminfo:

            mem_vals = line.split()
            key = mem_vals[0]
            mem = int(mem_vals[1])
            
            if key == "MemTotal:":
                mem_total = mem
            elif key == "MemFree:":
                mem_free = mem
            elif key == "Buffers:":
                mem_buffered = mem
            elif key == "Cached:":
                mem_cached = mem
            elif key == "SReclaimable:":
                mem_reclaimable = mem
            elif key == "Shmem":
                mem_shmem = mem

        mem_cached = mem_cached + (mem_reclaimable - mem_shmem)

        return {
            'total':    mem_total,
            'used':     mem_total - mem_free - (mem_buffered + mem_cached),
            'free':     mem_free,
            'buffered': mem_buffered,
            'cached':   mem_cached
        }

    def get_gpu_temp(self):
        """
        Returns the current temperature of the device's GPU
        """

        temp = subprocess.check_output([ 'vcgencmd', 'measure_temp' ])[5:-3]
        return float(temp)

    def get_cpu_usage(self):
        """
        Parses the usage stats for the device's CPU. This assumes that the Pi
        running this is a >Pi2B model and has four cores. This method returns
        a 0-1 percentage which is the current utilisation of each core.
        """

        cpu_stats = subprocess.check_output([ "cat", "/proc/stat"]).splitlines()[0:5]

        overall_utilisation = self._parse_cpu_line('overall', cpu_stats[0])
        core_0_utilisation  = self._parse_cpu_line('core0',   cpu_stats[1])
        core_1_utilisation  = self._parse_cpu_line('core1',   cpu_stats[2])
        core_2_utilisation  = self._parse_cpu_line('core2',   cpu_stats[3])
        core_3_utilisation  = self._parse_cpu_line('core3',   cpu_stats[4])

        return {
            'overall': overall_utilisation,
            'core0': core_0_utilisation,
            'core1': core_1_utilisation,
            'core2': core_2_utilisation,
            'core3': core_3_utilisation
        }

    def _parse_cpu_line(self, cpu_name, line):
        """
        Calculates the current utilisation for a single core. This requires
        a delta of the current values and the previous values, so an 
        instance of PiStats keeps a record of the previously recorded
        values.
        """

        utilisation = 0.0

        try:
            
            fields = [float(column) for column in line.strip().split()[1:]]

            idle  = fields[3] + fields[4]
            total = sum(fields)

            delta_idle  = idle - self._previous_cpu_raw['idle'][cpu_name]
            delta_total = total - self._previous_cpu_raw['total'][cpu_name]

            self._previous_cpu_raw['idle'][cpu_name]  = idle
            self._previous_cpu_raw['total'][cpu_name] = total

            utilisation = (delta_total - delta_idle) / delta_total

        except Exception as e:
            pass

        return utilisation

class PiStatsRequestHandler(BaseHTTPRequestHandler):

    def __init__(self, pi_stats, *args):
        """
        Handles incoming HTTP requests. For each GET request,
        this handler will collect all current stats for the device
        and will return them as a JSON payload.
        """

        self.pi_stats = pi_stats
        BaseHTTPRequestHandler.__init__(self, *args)

    def _set_headers(self):

        self.send_response(200)
        self.send_header('Content-Type', "application/json")
        self.end_headers()

    def do_HEAD(self):
        self._set_headers()

    def do_GET(self):

        stats = {
            'cpu_usage': self.pi_stats.get_cpu_usage(),
            'gpu_temp':  self.pi_stats.get_gpu_temp(),
            'memory':    self.pi_stats.get_mem_usage()
        }

        network_stats = self.pi_stats.get_network_bytes()

        all_stats = stats.copy()
        all_stats.update(network_stats)

        self._set_headers();
        self.wfile.write(json.dumps(all_stats))

class PiStatsServer:

    def __init__(self, port, pi_stats):

        def handler(*args):
            PiStatsRequestHandler(pi_stats, *args)

        server = HTTPServer(("", port), handler)
        server.serve_forever()

class Main:

    def __init__(self, port):
        self.pi_stats = PiStats()
        self.server   = PiStatsServer(port, self.pi_stats)

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=3000, help="The HTTP port the server will run off")

    args = parser.parse_args()

    Main(args.port)
    
