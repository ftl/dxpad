#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, re, time

from . import _time

QSL_BURO = "Büro"
QSL_DIRECT = "direkt"
QSL_LOTW = "LotW"
QSL_EQSL = "eQSL"

CALL_EXPRESSION = re.compile(r'\b(([A-Z0-9]+)/)?([A-Z0-9]?[A-Z][0-9][A-Z0-9]*[A-Z])(/([A-Z0-9]+))?(/(P|A|M|MM|AM))?\b', re.IGNORECASE)

class Call:
	def __init__(self, raw_text):
		if not Call.is_valid_call(raw_text): raise ValueError("{} is not a valid call.".format(raw_text))
		match = CALL_EXPRESSION.match(raw_text)
		if not(match):
			print("Cannot find call: " + raw_text)
		self.prefix = match.group(2).upper() if match.start(2) > -1 else None
		self.base_call = match.group(3).upper()
		self.suffix = match.group(5).upper() if match.start(5) > -1 else None
		self.working_condition = match.group(7).upper() if match.start(7) > -1 else None
		if self.suffix in ["P", "A", "M", "MMJO68", "AM"] and not self.working_condition:
			self.working_condition = self.suffix
			self.suffix = None

	def __repr__(self):
		return "Call(\"{}\")".format(str(self))

	def __str__(self):
		result = ""
		if self.prefix: result += self.prefix + "/"
		result += self.base_call
		if self.suffix: result += "/" + self.suffix
		if self.working_condition: result += "/" + self.working_condition
		return result

	def __hash__(self):
		return hash((self.prefix, self.base_call, self.suffix, self.working_condition))

	def __eq__(self, other):
		return hash(self) == hash(other)

	def __ne__(self, other):
		return hash(self) != hash(other)

	@staticmethod
	def is_valid_call(call):
		return len(CALL_EXPRESSION.findall(call)) == 1

	@staticmethod
	def find_all(text, map_func = lambda m: Call(m.group())):
		matches = CALL_EXPRESSION.finditer(text)
		return list(map(map_func, matches))

class Info:
	def __init__(self, call):
		self.call = call
		self.last_touch = time.time()
		self.qrz_id = None
		self.hamqth_id = None
		self.dxcc_info = None
		self.iota = None
		self.dok = None
		self.name = None
		self.postal_address = None
		self.latlon = None
		self.locator = None
		self.email = None
		self.qsl_service = None
		self.qsl_via = None

	def __str__(self):
		result = "*" * (len(str(self.call)) + 4) + "\n"
		result += "* " + str(self.call) + " *\n"
		result += "*" * (len(str(self.call)) + 4) + "\n"
		if self.name:
			result += "name: " + self.name + "\n"
		if self.postal_address:
			result += "address: " + "\n".join(self.postal_address) + "\n"
		if self.dok:
			result += "dok: " + self.dok + "\n"
		if self.dxcc_info:
			result += "country: " + self.dxcc_info.name + "\n"
			result += "continent: " + self.dxcc_info.continent + " itu: " + str(self.dxcc_info.itu_zone) + " cq: " + str(self.dxcc_info.cq_zone) + "\n"
		if self.iota:
			result += "iota: " + self.iota + "\n"
		if self.latlon:
			result += "lat/lon: " + str(self.latlon) + "\n"
		if self.locator:
			result += "grid: " + str(self.locator) + "\n"
		if self.email:
			result += "email: " + str(self.email) + "\n"
		if self.qrz_id:
			result += "qrz.com: " + self.qrz_id + "\n"
		if self.qsl_service:
			result += "QSL: " + ", ".join(self.qsl_service) + "\n"
		if self.qsl_manager:
			result += "QSL via: " + self.qsl_via + "\n"

		result += "last touch: {}".format(_time.z(self.last_touch))

		return result

	def touch(self):
		self.last_touch = time.time()

	def distance_to(self, locator):
		if self.latlon:
			return self.latlon.distance_to(locator.to_lat_lon())
		elif self.locator:
			return self.locator.distance_to(locator)
		return 0

	def bearing_to(self, locator):
		if self.latlon:
			return self.latlon.bearing_to(locator.to_lat_lon())
		elif self.locator:
			return self.locator.bearing_to(locator)
		return 0

	def bearing_from(self, locator):
		if self.latlon:
			return self.latlon.bearing_from(locator.to_lat_lon())
		elif self.locator:
			return self.locator.bearing_from(locator)
		return 0
