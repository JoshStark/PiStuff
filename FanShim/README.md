## LibreELEC Fan Shim

This is a modification/rewrite of Pimoroni's own python code for controlling their Fan Shim based on temperature changes. If you are interested in seeing how they've approached it, I recommend looking at [their own GitHub repo](https://github.com/pimoroni/fanshim-python).

This works by running a python script which monitors the current temperature of the Raspberry Pi and turns the Fan Shim on or off if the temperature breaches the upper or lower thresholds.

### Why not just use the Pimoroni code?
Unfortunately LibreELEC's core system has very limited dependencies installed so the official code won't quite work out of the box. This is a slightly reworked and cut down version with LibreELEC directly in mind.

### Installation

Firstly you'll need to install the Raspberry Pi Tools Add-on:

`Add-ons` -> `Install from repository` -> `LibreELEC Add-ons` -> `Program Add-ons` -> `Raspberry Pi Tools`.

This add-on installs the necessary GPIO libraries for python.

Next, grab the installer script:

```bash
wget https://raw.githubusercontent.com/JoshStark/PiStuff/master/FanShim/InstallLibreELECFanShim.sh -O /storage/InstallLibreELECFanShim.sh
chmod u+x InstallLibreELECFanShim.sh
```

This script will grab the latest version of the python code which runs the Fan Shim monitor. It has two arguments: `on_threshold` and `off_threshold`. These are optional but positional arguments so if you want to change the default value for `off_threshold` you must first provide a value for `on_threshold`. You don't need to set these if you don't want to; the default values are `65` and 45` respectively.

#### Install Script usage

```bash
# ./InstallLibreELECFanShim.sh <on_threshold> <off_threshold>
./InstallLibreELECFanShim.sh 65 45
```

The install script will download the python code and place it in `/storage/LibreELECFanShim/LibreELECFanShim.py`.
It will then attempt to kill any existing fan shim processes (if you run the installer script again to update, for example).
It will also check LibreELEC's autostart script and will update its record in there accordingly.
Finally a new process will be spawned and the monitor should start running.
