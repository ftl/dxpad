#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
For more information about grayline see https://github.com/joergdietrich/Leaflet.Terminator/blob/master/L.Terminator.js
For more information about sunrise/sunset see http://michelanders.blogspot.de/2010/12/calulating-sunrise-and-sunset-in-python.html
"""

import sys, math, time

def days_since_epoch(time = time.time()):
    return time / 86400.0

def days_to_gmst(days):
    return (18.697374558 + 24.06570982441908 * days) % 24

def deg_to_rad(deg):
    return deg * math.pi / 180.0

def rad_to_deg(rad):
    return rad * 180.0 / math.pi

def _ecliptic_position(days):
    lon = (280.460 + 0.9856003 * days) % 360.0
    g = (357.528 + 0.9856003 * days) % 360.0

    ecliptic_lon = (lon + 1.915 * math.sin(deg_to_rad(g)) 
                        + 0.02 * math.sin(deg_to_rad(2 * g)))
    r = (1.00014 - 0.01671 * math.cos(deg_to_rad(g)) 
         - 0.0014 * math.cos(deg_to_rad(2 * g)))
    return (ecliptic_lon, r)

def _ecliptic_obliquity(days):
    centuries = days / 36525.0
    return (23.43929111 
             - centuries * (46.836769 / 3600.0 
                 - centuries * (0.0001831 / 3600.0 
                     + centuries * (0.00200340 / 3600.0 
                         - centuries * (0.576e-6 / 3600.0 
                             - centuries * 4.34e-8 / 3600.0)))))

def _equitorial_position(ecliptic_lon, ecliptic_obliquity):
    alpha = rad_to_deg(
        math.atan(math.cos(deg_to_rad(ecliptic_obliquity)) 
                    * math.tan(deg_to_rad(ecliptic_lon))))
    delta = rad_to_deg(
        math.asin(math.sin(deg_to_rad(ecliptic_obliquity)) 
                    * math.sin(deg_to_rad(ecliptic_lon))))
    l_quadrant = math.floor(ecliptic_lon / 90) * 90
    ra_quadrant = math.floor(alpha / 90) * 90
    alpha += l_quadrant - ra_quadrant

    return (alpha, delta)

def _hour_angle(lon, equitorial_position, gmst):
    lst = gmst + lon / 15.0
    return lst * 15.0 - equitorial_position[0]

def _latitude(angle, equitorial_position):
    return -rad_to_deg(
        math.atan(-math.cos(deg_to_rad(angle)) 
                    / math.tan(deg_to_rad(equitorial_position[1]))))

def calculate_day_night_terminator(time):
    days = days_since_epoch(time)
    gmst = days_to_gmst(days)
    ecliptic_position = _ecliptic_position(days)
    ecliptic_obliquity = _ecliptic_obliquity(days)
    equitorial_position = _equitorial_position(
        ecliptic_position[0], ecliptic_obliquity)

    polygon = []
    for i in range(0, 361):
        lon = -180.0 + i
        angle = _hour_angle(lon, equitorial_position, gmst)
        lat = _latitude(angle, equitorial_position)
        polygon.append((lat, lon))

    if equitorial_position[1] > 0:
        polygon.insert(0, (-90, -180))
        polygon.append((-90, 180))
    else:
        polygon.insert(0, (90, -180))
        polygon.append((90, 180))

    return polygon
