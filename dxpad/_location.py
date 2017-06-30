#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
representation of coordinates as latitude/longitude

distance calculations: https://gist.github.com/rochacbruno/2883505
more calculations: http://www.movable-type.co.uk/scripts/latlong.html
"""

import math

def norm_lat(lat):
    return max(-90.0, min(lat, 90.0))

def norm_lon(lon):
    if lon < -180: return lon + 360
    if lon >= 180: return lon - 360
    return lon

class LatLon:
    def __init__(self, lat, lon):
        self.lat = norm_lat(lat)
        self.lon = norm_lon(lon)

    def __hash__(self):
        return hash((self.lat, self.lon))

    def __eq__(self, other):
        return int(self.lat * 10000) == int(other.lat * 10000) and int(self.lon * 10000) == int(other.lon * 10000) 

    def __repr__(self):
        return "LatLon({:8.5f}, {:8.5f})".format(self.lat, self.lon)

    def __str__(self):
        return "({:8.5f}/{:8.5f})".format(self.lat, self.lon)

    def distance_to(self, other):
        radius = 6371 # km
        d_lat = math.radians(other.lat - self.lat)
        d_lon = math.radians(other.lon - self.lon)
        a = math.pow(math.sin(d_lat / 2) , 2) + math.cos(math.radians(self.lat)) * math.cos(math.radians(other.lat)) * math.pow(math.sin(d_lon / 2), 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return radius * c

    def bearing_to(self, other):
        lat1 = math.radians(self.lat)
        lat2 = math.radians(other.lat)
        d_lon = math.radians(other.lon - self.lon)
        y = math.sin(d_lon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(d_lon)
        bearing = math.degrees(math.atan2(y, x))
        return (bearing + 360.0) % 360.0

    def bearing_from(self, other):
        return (self.bearing_to(other) + 180.0) % 360.0

    def neighbours(self):
        lat = int(self.lat)
        lon = int(self.lon / 2) * 2
        neighbours = set()
        for d_lon in range(-1, 2):
            for d_lat in range(-1, 2):
                    neighbours.add(LatLon(lat + d_lat, lon + d_lon * 2))
        return neighbours - set([self])
