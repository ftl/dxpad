#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Lookup callbook information at hamqth.com.

For more information about the API see https://www.hamqth.com/developers.php
"""

import sys, requests, collections
import xml.dom.minidom as minidom
from PySide import QtCore, QtGui

from . import _callinfo, _grid, _location, _xml

def _is_not_empty(text):
	return text and text.strip() != ""

class HamQTH:
	def __init__(self, username, password):
		self.username = username
		self.password = password
		self.session = None

	def lookup_call(self, call):
		if not self._login(): return None
		response = self._get({"id": self.session.session_id, "callsign": str(call), "prg": "dxpad0.0"})
		if not response:
			print("HamQTH: query failed")
			return None
		if response.error == "Session does not exist or expired": 
			self.session = None
			return self.lookup_call(call)
		return self._to_callinfo(call, response.search)

	def _login(self):
		if self.session and self.session.Key: return True
		response = self._get({"u": self.username, "p": self.password})
		if not response:
			print("HamQTH: login failed")
			return False
		self.session = response.session
		return self.session and self.session.session_id

	def _get(self, params):
		response = requests.get("https://www.hamqth.com/xml.php", params = params)
		if response.status_code != 200:
			print("HamQTH: request failed")
			print(str(response.status_code))
			print(response.text)
			return None
		return _xml.XMLDataElement.from_string(response.text)

	def _to_callinfo(self, call, info):
		if not info: return None

		result = _callinfo.Info(call)
		result.hamqth_id = info.callsign
		result.email = info.email
		result.name = info.nick
		result.postal_address = [s for s in [info.adr_name, info.adr_street1, info.adr_street2, info.adr_street3, info.adr_city, info.adr_zip] if s != None and s.strip() != ""]
		if info.latitude and info.longitude:
			result.latlon = _location.LatLon(float(info.latitude), float(info.longitude))
		if info.grid and _grid.Locator.is_valid_locator(info.grid):
			result.locator = _grid.Locator(info.grid)
		elif result.latlon:
			result.locator = _grid.Locator.from_lat_lon(result.latlon)
		result.iota = info.iota
		result.dok = info.dok
		result.qsl_via = info.qsl_via if _is_not_empty(info.qsl_via) else None
		result.qsl_service = set([])
		if info.qsl == "Y":
			result.qsl_service.add(_callinfo.QSL_BURO)
		if info.qsldirect == "Y":
			result.qsl_service.add(_callinfo.QSL_DIRECT)
		if info.lotw == "Y":
			result.qsl_service.add(_callinfo.QSL_LOTW)
		if info.eqsl == "Y":
			result.qsl_service.add(_callinfo.QSL_EQSL)

		return result

class AsyncHamQTH(QtCore.QThread):
	call_info = QtCore.Signal(object, object)

	def __init__(self, username, password, parent = None):
		QtCore.QThread.__init__(self, parent)
		self.hamqth = HamQTH(username, password)
		self.requested_calls = collections.deque([])

	def run(self):
		while len(self.requested_calls) > 0:
			requested_call = self.requested_calls.popleft()
			info = self.hamqth.lookup_call(requested_call)
			if not info and hasattr(requested_call, "base_call"):
				info = self.hamqth.lookup_call(requested_call.base_call)
			if info:
				self.call_info.emit(requested_call, info)

	@QtCore.Slot(object)
	def lookup_call(self, call):
		self.requested_calls.append(call)
		self.start()

@QtCore.Slot(object)
def print_call_info(call, info):
	print(str(call) + ": " + info.fname + " " + info.name + " from " + info.country)

def main(args):
	if len(args) < 3: return

	app = QtGui.QApplication(sys.argv)

	hamqth = HamQTH(args[1], args[2])
	for call in args[3:]:
		info = hamqth.lookup_call(_callinfo.Call(call))
		print(str(info))

if __name__ == "__main__": main(sys.argv)
