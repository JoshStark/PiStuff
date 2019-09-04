#!/usr/bin/env python

import argparse
import time
import subprocess
import json
import os

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

class PiStatsRequestHandler(BaseHTTPRequestHandler):

    def __init__(self, pi_stats, *args):
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
            'gpu_temp': self.pi_stats.get_gpu_temp(),
            'memory': self.pi_stats.get_mem_usage()
        }

        network_stats = self.pi_stats.get_network_bytes()

        all_stats = stats.copy()
        all_stats.update(network_stats)

        self._set_headers();
        self.wfile.write(json.dumps(all_stats))

class PiStats():

    def __init__(self):

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

        ifaces = {}

        interfaces_available = subprocess.check_output([ "ls", "/sys/class/net" ]).split()
        for iface in interfaces_available:

            rx = long(subprocess.check_output([ "cat", "/sys/class/net/{}/statistics/rx_bytes".format(iface) ]))
            tx = long(subprocess.check_output([ "cat", "/sys/class/net/{}/statistics/tx_bytes".format(iface) ]))

            ifaces["net_{}".format(iface)] = { 'tx': tx, 'rx': rx}

        return ifaces

    def get_mem_usage(self):

        p = os.popen('free')
        
        i = 0
        while i < 100:
            
            i = i + 1
            line = p.readline()
            if i == 2:
                
                stats = line.split()[1:4]
                return {
                    'total': int(stats[0]),
                    'used': int(stats[1]),
                    'free': int(stats[2]),
                    'shared': int(stats[3]),
                    'buffered': int(stats[4]),
                    'cached': int(stats[5])
                }

        return {
            'total': 0,
            'used': 0,
            'free': 0
        }

    def get_gpu_temp(self):

        temp = subprocess.check_output([ 'vcgencmd', 'measure_temp' ])[5:-3]
        return float(temp)

    def get_cpu_usage(self):

        with open("/proc/stat") as f:

            overall_utilisation = self._parse_cpu_line('overall', f.readline())
            core_0_utilisation  = self._parse_cpu_line('core0', f.readline())
            core_1_utilisation  = self._parse_cpu_line('core1', f.readline())
            core_2_utilisation  = self._parse_cpu_line('core2', f.readline())
            core_3_utilisation  = self._parse_cpu_line('core3', f.readline())

        return {
            'overall': overall_utilisation,
            'core0': core_0_utilisation,
            'core1': core_1_utilisation,
            'core2': core_2_utilisation,
            'core3': core_3_utilisation
        }

    def _parse_cpu_line(self, cpu_name, line):

        utilisation = 0.0

        try:
            
            fields = [float(column) for column in line.strip().split()[1:]]

            idle  = fields[3] + fields[4]
            total = sum(fields)

            delta_idle = idle - self._previous_cpu_raw['idle'][cpu_name]
            delta_total = total - self._previous_cpu_raw['total'][cpu_name]

            self._previous_cpu_raw['idle'][cpu_name]  = idle
            self._previous_cpu_raw['total'][cpu_name] = total

            utilisation = (delta_total - delta_idle) / delta_total

        except Exception as e:
            pass

        return utilisation

class PiStatsServer:

    def __init__(self, port, pi_stats):

        def handler(*args):
            PiStatsRequestHandler(pi_stats, *args)

        server = HTTPServer(("", port), handler)
        server.serve_forever()

class Main:

    def __init__(self, port):
        self.pi_stats = PiStats()
        self.server = PiStatsServer(port, self.pi_stats)

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=1337, help='The HTTP port the server will run off')

    args = parser.parse_args()

    Main(args.port)
    
