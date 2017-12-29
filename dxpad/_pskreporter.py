#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Retrieving spots from pskreporter.info.

For more information see: https://www.pskreporter.info/pskdev.html
template URL: retrieve.pskreporter.info/query?senderCallsign=jn&rronly=1&modify=grid&flowStartSeconds=-600
"""

import sys
import requests
import time
import xml.dom.minidom as minidom

from PySide import QtCore, QtGui

from . import _spotting, _callinfo, _grid, _location, _config

class PskReporterSpot(_spotting.Spot):
    TTL = 600
    def __init__(
            self, call, frequency, time, source_call, source_grid, mode, snr):
        _spotting.Spot.__init__(
            self, self.TTL, call, frequency, time, source_call, source_grid)
        self.mode = mode
        self.snr = snr

    def __str__(self):
        return ("{} pskreporter(mode: {}, snr: {})"
                .format(_spotting.Spot.__str__(self), self.mode, self.snr))

    def __hash__(self):
        return hash(
            (self.source_call, self.call, self.frequency, self.time, self.mode,
                self.snr))

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __ne__(self, other):
        return hash(self) != hash(other)


class PskReporterWorker(QtCore.QThread):
    MAX_SNR = 30.0
    MIN_REQUEST_TIME = 200.0
    spot_received = QtCore.Signal(object)

    def __init__(self, own_call, grid, parent = None):
        QtCore.QThread.__init__(self, parent)
        self.own_call = own_call
        self.grid = grid
        self.dx_call = None
        self.query_last_request = {}

    @QtCore.Slot(str)
    def set_dx_call(self, dx_call):
        self.dx_call = dx_call
        self.start()

    def run(self):
        queries = [
            {"senderCallsign": self.own_call, "rronly": "1", "flowStartSeconds": "-600"},
            {"receiverCallsign": self.own_call, "rronly": "1", "flowStartSeconds": "-600"},
            {"senderCallsign": self.dx_call, "rronly": "1", "flowStartSeconds": "-600"},
            {"receiverCallsign": self.dx_call, "rronly": "1", "flowStartSeconds": "-600"},
            {"rronly": "1", "flowStartSeconds": "-600"}
        ]
        self._run_queries(queries)

    def _run_queries(self, queries):
        unique_spots = set()
        for query in queries:
            self._run_query(query, unique_spots)

    def _run_query(self, query, unique_spots):
        print("PskReporter: fetch spots " + str(query))

        xml_data = self._request_spots(query)
        if not(xml_data):
            return
        
        spot_count = 0
        for element in xml_data.getElementsByTagName("receptionReport"):
            incoming_spot = self._element_to_spot(element)
            if not(incoming_spot): 
                continue
            
            #if not(incoming_spot in unique_spots):
            self.spot_received.emit(incoming_spot)
            #unique_spots.add(incoming_spot)
            spot_count += 1

        print("PskReporter: received {} spots".format(spot_count))

    def _request_spots(self, query):
        if not(self._is_query_valid(query)):
            return None

        response = requests.get(
            "http://retrieve.pskreporter.info/query", 
            params = query)
        if response.status_code != 200:
            print("PskReporter: request failed")
            print(str(response.status_code))
            print(response.text)
            return None
        return minidom.parseString(response.text)

    def _is_query_valid(self, query):
        for value in query.values():
            if not(value): 
                print("PskReporter: not all query parameters have a valid value")
                return False

        query_hash = hash(tuple(sorted(query.keys()) + sorted(query.values())))
        now = time.time()

        if query_hash in self.query_last_request:
            last_request = self.query_last_request[query_hash]
            if now - last_request < self.MIN_REQUEST_TIME:
                print("PskReporter: the last request of this query is too close: " + str(now - last_request))
                return False

        self.query_last_request[query_hash] = now
        return True

    def _element_to_spot(self, element):
        if not (_callinfo.Call.is_valid_call(
                    element.getAttribute("receiverCallsign")) 
                and _grid.Locator.is_valid_locator(
                    element.getAttribute("receiverLocator")) 
                and _callinfo.Call.is_valid_call(
                    element.getAttribute("senderCallsign")) 
                and element.hasAttribute("frequency")): 
            return None
        
        source_call = _callinfo.Call(element.getAttribute("receiverCallsign"))
        source_grid = _grid.Locator(element.getAttribute("receiverLocator"))
        call = _callinfo.Call(element.getAttribute("senderCallsign"))
        frequency = int(element.getAttribute("frequency")) / 1000
        time = int(element.getAttribute("flowStartSeconds"))
        mode = element.getAttribute("mode")
        snr = float(element.getAttribute("sNR")) if element.hasAttribute("sNR") else 0.0
        normalized_snr = snr if snr >= 0.0 else self.MAX_SNR + snr

        return PskReporterSpot(call, frequency, time, source_call,
            source_grid, mode, normalized_snr)


class PskReporter(QtCore.QObject):
    spot_received = QtCore.Signal(object)

    def __init__(self, own_call, own_locator, parent = None):
        QtCore.QObject.__init__(self, parent)
        self.worker = PskReporterWorker(str(own_call), str(own_locator)[:2])
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

    @QtCore.Slot(object)
    def set_dx_call(self, dx_call):
        self.worker.set_dx_call(str(dx_call))


def print_spot(spot):
    print(str(spot))

def main(args):
    app = QtGui.QApplication(sys.argv)

    wid = QtGui.QWidget()
    wid.resize(250, 150)
    wid.setWindowTitle('Simple')
    wid.show()

    config = _config.load_config()

    psk_reporter = PskReporter(config.call, config.locator)
    psk_reporter.spot_received.connect(print_spot)
    psk_reporter.set_dx_call("GM0HUU")
    psk_reporter.start()

    result = app.exec_()

    psk_reporter.stop()

    sys.exit(result)

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