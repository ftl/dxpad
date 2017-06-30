#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
representation of coordinates as grid square locators
conversion between locators and latitude/longitude coordinates

see https://en.wikipedia.org/wiki/Maidenhead_Locator_System
see http://ham.stackexchange.com/questions/221/how-can-one-convert-from-lat-long-to-grid-square
"""

import sys, re, math

from . import _location

LOCATOR_EXPRESSION = re.compile(r'[A-R]{2}([0-9]{2}([a-x]{2})?)?', re.IGNORECASE)

class Locator:
    def __init__(self, locator):
        self.locator = self.format_as_locator(locator)

    @staticmethod
    def is_valid_locator(locator):
        return len(locator) >= 2 and len(locator) <= 6 and len(LOCATOR_EXPRESSION.findall(locator)) == 1

    def format_as_locator(self, locator):
        if not Locator.is_valid_locator(locator):
            raise ValueError("{} is not a valid locator.".format(locator))
        result = locator[0:2].upper()
        if len(locator) > 2:
            result += locator[2:4]
        if len(locator) > 4:
            result += locator[4:6].lower()
        return result

    def __str__(self):
        return self.locator

    def __hash__(self):
        return hash(self.locator)

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __ne__(self, other):
        return hash(self) != hash(other)

    def distance_to(self, other):
        return self.to_lat_lon().distance_to(other.to_lat_lon())

    def bearing_to(self, other):
        return self.to_lat_lon().bearing_to(other.to_lat_lon())

    def bearing_from(self, other):
        return self.to_lat_lon().bearing_from(other.to_lat_lon())

    def to_lat_lon(self):
        lon = (ord(self.locator[0]) - ord("A")) * 20.0
        lat = (ord(self.locator[1]) - ord("A")) * 10.0
        if len(self.locator) > 2:
            lon += int(self.locator[2]) * 2.0
            lat += int(self.locator[3])
        if len(self.locator) > 4:
            lon += (ord(self.locator[4]) - ord("a")) / 12.0
            lat += (ord(self.locator[5]) - ord("a")) / 24.0

        lon -= 180.0
        lat -= 90.0

        return _location.LatLon(lat, lon)

    @staticmethod
    def from_lat_lon(latlon, precision = 6):
        lon = latlon.lon + 180.0
        lat = latlon.lat + 90.0
        field = chr(ord("A") + int(lon // 20)) + chr(ord("A") + int(lat // 10))
        square = str(int((lon / 2) % 10)) + str(int(lat % 10))
        subsquare = chr(ord("a") + int((lon - 2 * int(lon / 2)) * 12.0)) + chr(ord("a") + int((lat - int(lat)) * 24.0))
        locator = field
        if precision > 2: locator += square
        if precision > 4: locator += subsquare
        return Locator(locator)


def main(args):
    if Locator.is_valid_locator(args[1]):
        locator = Locator(args[1])
        latlon = locator.to_lat_lon()
        if len(args) > 2 and Locator.is_valid_locator(args[2]):
            locator2 = Locator(args[2])
            distance = locator.distance_to(locator2)
            bearing_to = locator.bearing_to(locator2)
            bearing_from = locator.bearing_from(locator2)
            print(("{!s} -> {!s}: {:.0f}km".format(locator, locator2, distance)))
            print(("{!s} -> {!s}: {:.1f}°".format(locator, locator2, bearing_to)))
            print(("{!s} -> {!s}: {:.1f}°".format(locator, locator2, bearing_from)))
            print(("{!s} == {!s}: {}".format(locator, locator2, str(locator == locator2))))
    else:
        lat = float(args[1])
        lon = float(args[2])
        latlon = _location.LatLon(lat, lon)
        locator = Locator.from_lat_lon(latlon)

    print(("{!s} = {!s}".format(locator, latlon)))

if __name__ == "__main__": main(sys.argv)