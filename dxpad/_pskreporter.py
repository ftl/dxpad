#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Retrieving spots from pskreporter.info.

For more information see: https://www.pskreporter.info/pskdev.html
# retrieve.pskreporter.info/query?senderCallsign=jn&rronly=1&modify=grid&flowStartSeconds=-600
"""

import sys, requests
import xml.dom.minidom as minidom
from PySide import QtCore, QtGui

from . import _spotting, _callinfo, _grid, _location, _config

class PskReporterSpot(_spotting.Spot):
    TTL = 600
    def __init__(self, call, frequency, time, source_call, source_grid, mode, snr):
        _spotting.Spot.__init__(self, self.TTL, call, frequency, time, source_call, source_grid)
        self.mode = mode
        self.snr = snr

    def __str__(self):
        return _spotting.Spot.__str__(self) + " pskreporter(mode: {}, snr: {})".format(self.mode, self.snr)

class PskReporterWorker(QtCore.QThread):
    MAX_SNR = 30.0
    spot_received = QtCore.Signal(object)

    def __init__(self, grid, parent = None):
        QtCore.QThread.__init__(self, parent)
        self.grid = grid

    def run(self):
        print("PskReporter: fetch spots")
        response = requests.get("http://retrieve.pskreporter.info/query", params = {"senderCallsign": self.grid, "rronly": "1", "modify": "grid", "flowStartSeconds": "-600"})
        if response.status_code != 200:
            print("PskReporter: request failed")
            print(str(response.status_code))
            print(response.text)
            return
        xml_data = minidom.parseString(response.text)
        for element in xml_data.getElementsByTagName("receptionReport"):
            if not (_callinfo.Call.is_valid_call(element.getAttribute("receiverCallsign")) 
                and _grid.Locator.is_valid_locator(element.getAttribute("receiverLocator")) 
                and _callinfo.Call.is_valid_call(element.getAttribute("senderCallsign")) 
                and element.hasAttribute("frequency")): 
                continue
            
            source_call = _callinfo.Call(element.getAttribute("receiverCallsign"))
            source_grid = _grid.Locator(element.getAttribute("receiverLocator"))
            call = _callinfo.Call(element.getAttribute("senderCallsign"))
            frequency = int(element.getAttribute("frequency")) / 1000
            time = int(element.getAttribute("flowStartSeconds"))
            mode = element.getAttribute("mode")
            snr = float(element.getAttribute("sNR")) if element.hasAttribute("sNR") else 0.0
            normalized_snr = snr if snr >= 0.0 else self.MAX_SNR + snr

            incoming_spot = PskReporterSpot(call, frequency, time, source_call, source_grid, mode, normalized_snr)
            self.spot_received.emit(incoming_spot)


class PskReporter(QtCore.QObject):
    spot_received = QtCore.Signal(object)

    def __init__(self, own_locator, parent = None):
        QtCore.QObject.__init__(self, parent)
        self.worker = PskReporterWorker(str(own_locator)[:2])
        self.worker.spot_received.connect(self._spot_received)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.worker.start)
        self.timer.setInterval(240000)

    def _spot_received(self, spot):
        self.spot_received.emit(spot)

    def start(self):
        self.worker.start()
        self.timer.start()

    def stop(self):
        self.timer.stop()
        self.worker.wait()


def print_spot(spot):
    print(str(spot))

def main(args):
    app = QtGui.QApplication(sys.argv)

    wid = QtGui.QWidget()
    wid.resize(250, 150)
    wid.setWindowTitle('Simple')
    wid.show()

    config = _config.load_config()

    psk_reporter = PskReporter(config.locator)
    psk_reporter.spot_received.connect(print_spot)
    psk_reporter.start()

    result = app.exec_()

    psk_reporter.stop()

    sys.exit(result)


if __name__ == "__main__": main(sys.argv)

"""
<receptionReport 
    receiverCallsign="SM6FMB" -> source_call
    receiverLocator="JO57vo" -> source_grid
    senderCallsign="IK6FAW" -> call
    senderLocator="JN62SU" 
    frequency="14031000" -> frequency
    flowStartSeconds="1490366343" -> time
    mode="CW" -> mode
    isSender="1" 
    receiverDXCC="Sweden" 
    receiverDXCCCode="SM" 
    senderLotwUpload="2017-03-04" 
    sNR="12"/> -> SNR
"""