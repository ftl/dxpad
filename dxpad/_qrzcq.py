#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Lookup callbook information at qrzcq.com.

For more information about the API see 
https://www.qrzcq.com/docs/api/xml/
"""

import sys
import requests
import collections
import xml.dom.minidom as minidom

from PySide import QtCore, QtGui

from . import _callinfo, _grid, _location, _xml

class Qrzcq:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session = None

    def lookup_call(self, call):
        if not self._login(): 
            return None
        response = self._get({"s": self.session.Key, "callsign": str(call)})
        if not response:
            print("QRZCQ: query failed")
            return None
        self.session = response.Session
        if self.session.Error == "Session Timeout": 
            return self.lookup_call(call)
        return self._to_callinfo(call, response.Callsign)

    def _login(self):
        if self.session and self.session.Key: 
            print("Already logged in: " + str(self.session))
            return True
        response = self._get(
            {"username": self.username, "password": self.password, 
                "agent": "dxpad0.0"})
        if not response:
            print("QRZCQ: login failed")
            return False
        self.session = response.Session
        print("Logged in: " + str(self.session))
        return self.session and self.session.Key

    def _get(self, params):
        response = requests.get(
            "https://ssl.qrzcq.com/xml", params = params)
        if response.status_code != 200:
            print("QRZCQ: request failed")
            print(str(response.status_code))
            print(response.text)
            return None
        return _xml.XMLDataElement.from_string(response.text)

    def _to_callinfo(self, call, input_info):
        if not input_info: return None

        result = _callinfo.Info(call)
        result.qrz_id = input_info.call
        result.email = input_info.email
        result.dok = input_info.dok
        if input_info.fname or input_info.name:
            result.name = " ".join(
                [s for s in [input_info.fname, input_info.name] if s != None])
        result.postal_address = [s for s 
                in [input_info.addr1, input_info.addr2, input_info.zip] if s != None]
        if input_info.lat and input_info.lon:
            result.latlon = _location.LatLon(
                float(input_info.lat), float(input_info.lon))
        if input_info.grid:
            result.locator = _grid.Locator(input_info.grid)
        elif result.latlon:
            result.locator = _grid.Locator.from_lat_lon(result.latlon)
        result.qsl_service = set([])
        if input_info.mqsl == "1":
            result.qsl_service.add(_callinfo.QSL_DIRECT)
        if input_info.lotw == "1":
            result.qsl_service.add(_callinfo.QSL_LOTW)
        if input_info.eqsl == "1":
            result.qsl_service.add(_callinfo.QSL_EQSL)

        return result

class AsyncQrzcq(QtCore.QThread):
    call_info = QtCore.Signal(object, object)

    def __init__(self, username, password, parent = None):
        QtCore.QThread.__init__(self, parent)
        self.qrzcq= Qrzcq(username, password)
        self.requested_calls = collections.deque([])

    def run(self):
        while len(self.requested_calls) > 0:
            requested_call = self.requested_calls.popleft()
            info = self.qrzcq.lookup_call(requested_call)
            if not info and hasattr(requested_call, "base_call"):
                info = self.qrzcq.lookup_call(requested_call.base_call)
            if info:
                self.call_info.emit(requested_call, info)

    @QtCore.Slot(object)
    def lookup_call(self, call):
        self.requested_calls.append(call)
        self.start()

@QtCore.Slot(object)
def print_call_info(call, info):
    print(
        "{} : {} {} from {}"
        .format(str(call), info.fname, info.name, info.country))

def main(args):
    if len(args) < 3: return

    app = QtGui.QApplication(sys.argv)

    qrzcq = Qrzcq(args[1], args[2])
    for call in args[3:]:
        info = qrzcq.lookup_call(_callinfo.Call(call))
        print(str(info))
