#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

class Range:
    def __init__(self, from_kHz, to_kHz):
        self.from_kHz = from_kHz
        self.to_kHz = to_kHz

    def contains(self, frequency):
        return frequency >= self.from_kHz and frequency < self.to_kHz

class Band(Range):
    def __init__(self, name, from_kHz, to_kHz, portions):
        Range.__init__(self, from_kHz, to_kHz)
        self.name = name
        self.portions = portions

    def find_portion(self, frequency):
        if not self.contains(frequency): return None
        for portion in self.portions:
            if portion.contains(frequency): return portion
        return None

class Portion(Range):
    def __init__(self, name, from_kHz, to_kHz):
        Range.__init__(self, from_kHz, to_kHz)
        self.name = name

# see https://www.darc.de/fileadmin/filemounts/referate/hf/Region1Bandplan_2Seiten_farbig_deutsch_01Juni2016_v3.pdf
IARU_REGION_1 = [
    Band("160m", 1810.0, 2000.0, [
            Portion("CW", 1810.0, 1838.0),
            Portion("Digi", 1838.0, 1840.0),
            Portion("SSB", 1840.0, 2000.0)
        ]),
    Band("80m", 3500.0, 3800.0, [
            Portion("CW", 3500.0, 3580.0),
            Portion("Digi", 3580.0, 3600.0),
            Portion("SSB", 3600.0, 3800.0)
        ]),
    Band("60m", 5351.5, 5366.5, [
            Portion("CW", 5351.5, 5354.0),
            Portion("SSB", 5354.0, 5366.0),
            Portion("CW", 5366.0, 5366.5)
        ]), 
    Band("40m", 7000.0, 7200.0, [
            Portion("CW", 7000.0, 7040.0),
            Portion("Digi", 7040.0, 7050.0),
            Portion("SSB", 7050.0, 7200.0)
        ]),
    Band("30m", 10100.0, 10150.0, [
            Portion("CW", 10100.0, 10130.0),
            Portion("Digi", 10130.0, 10150.0)
        ]),
    Band("20m", 14000.0, 14350.0, [
            Portion("CW", 14000.0, 14070.0),
            Portion("Digi", 14070.0, 14099.0),
            Portion("Baken", 14099.0, 14101.0),
            Portion("SSB", 14101.0, 14350.0)
        ]),
    Band("17m", 18068.0, 18168.0, [
            Portion("CW", 18068.0, 18095.0),
            Portion("Digi", 18095.0, 18109.0),
            Portion("Baken", 18109.0, 18111.0),
            Portion("SSB", 18111.0, 18168.0)
        ]),
    Band("15m", 21000.0, 21450.0, [
            Portion("CW", 21000.0, 21070.0),
            Portion("Digi", 21070.0, 21149.0),
            Portion("Baken", 21149.0, 21151.0),
            Portion("SSB", 21151.0, 21450.0)
        ]),
    Band("12m", 24890.0, 24990.0, [
            Portion("CW", 24890.0, 24915.0),
            Portion("Digi", 24915.0, 24929.0),
            Portion("Baken", 24929.0, 24931.0),
            Portion("SSB", 24931.0, 24990.0)
        ]),
    Band("10m", 28000.0, 29700.0, [
            Portion("CW", 28000.0, 28070.0),
            Portion("Digi", 28070.0, 28190.0),
            Portion("Baken", 28190.0, 28225.0),
            Portion("SSB", 28225.0, 29000.0),
            Portion("FM", 29000.0, 29700.0)
        ])
]

def main(args):
    if len(args) != 2: return

    frequency = float(args[1])

    for band in IARU_REGION_1:
        if band.contains(frequency):
            portion = band.find_portion(frequency)

            if portion:
                print(
                    "{}, {}: {:10.1f} kHz - {:10.1f} kHz"
                    .format(
                        band.name, portion.name, 
                        portion.from_kHz, portion.to_kHz))
            else:
                print(
                    "{}, unknown: {:10.1f} kHz - {:10.1f} kHz"
                    .format(band.name, band.from_kHz, band.to_kHz))
            return

    print("band not found for {:10.1f} kHz".format(frequency))
