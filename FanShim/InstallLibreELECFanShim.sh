#!/bin/bash
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

on_threshold=${1:=65}
off_threshold=${2:=45}

remote_fanshim_path="https://raw.githubusercontent.com/JoshStark/PiStuff/master/FanShim/LibreELECFanShim.py"
local_fanshim_dir="/storage/LibreELECFanShim"
local_fanshim_path="${local_fanshim_dir}/LibreELECFanShim.py"
autostart_path="/storage/.config/autostart.sh"
autostart_cmd="nohup /storage/LibreELECFanShim/LibreELECFanShim.py --on-threshold=${on_threshold} --off-threshold=${off_threshold} >/var/log/LibreELECFanShim.py 2>&1 &"

if [ ! -d $local_fanshim_dir ]; then
    echo "Creating new FanShim directory in: ${local_fanshim_dir}"
    mkdir $local_fanshim_dir
fi

if [ ! -f $autostart_path ]; then
    echo "Could not find autostart.sh at path ${autostart_path}. Will create it."
    touch $autostart_path
fi

current_process=$(ps aux | awk '/[L]ibreELECFanShim/ {print $1}')
if [[ $current_process ]]; then
    echo "Killing existing PID=${current_process}"
    kill $current_process
fi

wget $remote_fanshim_path -O $local_fanshim_path
chmod u+x $local_fanshim_path

if ! grep -q "LibreELECFanShim" $autostart_path; then
    echo "Inserting autostart command: ${autostart_cmd}"
    echo "${autostart_cmd}" >> $autostart_path
fi

echo "Starting LibreELECFanShim: ${autostart_cmd}"
eval $autostart_cmd