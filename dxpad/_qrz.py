#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Lookup callbook information at qrz.com.

For more information about the API see 
https://www.qrz.com/page/current_spec.html
"""

import sys
import requests
import collections
import xml.dom.minidom as minidom

from PySide import QtCore, QtGui

from . import _callinfo, _grid, _location, _xml

class Qrz:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session = None

    def lookup_call(self, call):
        if not self._login(): 
            return None
        response = self._get({"s": self.session.Key, "callsign": str(call)})
        if not response:
            print("QRZ: query failed")
            return None
        self.session = response.Session
        if self.session.Error == "Session Timeout": 
            return self.lookup_call(call)
        return self._to_callinfo(call, response.Callsign)

    def _login(self):
        if self.session and self.session.Key: 
            return True
        response = self._get(
            {"username": self.username, "password": self.password, 
                "agent": "dxpad0.0"})
        if not response:
            print("QRZ: login failed")
            return False
        self.session = response.Session
        return self.session and self.session.Key

    def _get(self, params):
        response = requests.get(
            "https://xmldata.qrz.com/xml/current/", params = params)
        if response.status_code != 200:
            print("QRZ: request failed")
            print(str(response.status_code))
            print(response.text)
            return None
        return _xml.XMLDataElement.from_string(response.text)

    def _to_callinfo(self, call, qrz_info):
        if not qrz_info: return None

        result = _callinfo.Info(call)
        result.qrz_id = qrz_info.call
        result.email = qrz_info.email
        if qrz_info.fname or qrz_info.name:
            result.name = " ".join(
                [s for s in [qrz_info.fname, qrz_info.name] if s != None])
        result.postal_address = [s for s 
                in [qrz_info.addr1, qrz_info.addr2, qrz_info.zip] if s != None]
        if qrz_info.lat and qrz_info.lon:
            result.latlon = _location.LatLon(
                float(qrz_info.lat), float(qrz_info.lon))
        if qrz_info.grid:
            result.locator = _grid.Locator(qrz_info.grid)
        elif result.latlon:
            result.locator = _grid.Locator.from_lat_lon(result.latlon)
        result.qsl_service = set([])
        if qrz_info.mqsl == "1":
            result.qsl_service.add(_callinfo.QSL_DIRECT)
        if qrz_info.lotw == "1":
            result.qsl_service.add(_callinfo.QSL_LOTW)
        if qrz_info.eqsl == "1":
            result.qsl_service.add(_callinfo.QSL_EQSL)

        return result

class AsyncQrz(QtCore.QThread):
    call_info = QtCore.Signal(object, object)

    def __init__(self, username, password, parent = None):
        QtCore.QThread.__init__(self, parent)
        self.qrz = Qrz(username, password)
        self.requested_calls = collections.deque([])

    def run(self):
        while len(self.requested_calls) > 0:
            requested_call = self.requested_calls.popleft()
            info = self.qrz.lookup_call(requested_call)
            if not info and hasattr(requested_call, "base_call"):
                info = self.qrz.lookup_call(requested_call.base_call)
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

    qrz = Qrz(args[1], args[2])
    for call in args[3:]:
        info = qrz.lookup_call(_callinfo.Call(call))
        print(str(info))
