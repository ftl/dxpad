#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import time
import unittest
sys.path.insert(0, os.path.abspath('..'))

import dxpad._spotting as _spotting
import dxpad._dxcc as _dxcc
import dxpad._callinfo as _callinfo
import dxpad._grid as _grid


class TestAggregation(unittest.TestCase):
    def test_spotReceived_callExists_sameFrequency_shouldAddSource(self):
        now = time.time()
        spot_call = _callinfo.Call("AA1BB")
        aggregator = _spotting.SpotAggregator(FakeDXCC())
        incoming_spot1 = _spotting.Spot(60, spot_call, 14070000, now - 1,
            _callinfo.Call("CT1XY"), _grid.Locator("JN12aa"))
        incoming_spot2 = _spotting.Spot(60, spot_call, 14070000, now,
            _callinfo.Call("CT2XY"), _grid.Locator("JN12aa"))
        aggregator.spot_received(incoming_spot1)
        aggregator.spot_received(incoming_spot2)

        self.assertEqual(len(aggregator.spots[spot_call]), 1)
        spot = aggregator.spots[spot_call][0]
        self.assertEqual(len(spot.sources), 2)

        for source in spot.sources:
            self.assertEqual(source.source_dxcc_info, "FakeDXCCInfo")
        self.assertEqual(spot.frequency, 14070000)
        self.assertEqual(spot.timeout, now + 60)
        self.assertEqual(spot.first_seen, now - 1)
        self.assertEqual(spot.last_seen, now)

    def test_spotReceived_callExists_differentFrequency_shouldAddSpot(self):
        now = time.time()
        spot_call = _callinfo.Call("AA1BB")
        aggregator = _spotting.SpotAggregator(FakeDXCC())
        incoming_spot1 = _spotting.Spot(60, spot_call, 14070000, now - 1,
            _callinfo.Call("CT1XY"), _grid.Locator("JN12aa"))
        incoming_spot2 = _spotting.Spot(60, spot_call, 7040000, now,
            _callinfo.Call("CT2XY"), _grid.Locator("JN12aa"))
        aggregator.spot_received(incoming_spot1)
        aggregator.spot_received(incoming_spot2)

        self.assertEqual(len(aggregator.spots[spot_call]), 2)

        spot1 = aggregator.spots[spot_call][0]
        self.assertEqual(len(spot1.sources), 1)
        for source in spot1.sources:
            self.assertEqual(source.source_dxcc_info, "FakeDXCCInfo")
        self.assertEqual(spot1.frequency, 14070000)
        self.assertEqual(spot1.timeout, now - 1 + 60)
        self.assertEqual(spot1.first_seen, now - 1)
        self.assertEqual(spot1.last_seen, now - 1)

        spot2 = aggregator.spots[spot_call][1]
        self.assertEqual(len(spot2.sources), 1)
        for source in spot2.sources:
            self.assertEqual(source.source_dxcc_info, "FakeDXCCInfo")
        self.assertEqual(spot2.frequency, 7040000)
        self.assertEqual(spot2.timeout, now + 60)
        self.assertEqual(spot2.first_seen, now)
        self.assertEqual(spot2.last_seen, now)

    def test_spotReceived_newCall_shouldAddSpot(self):
        now = time.time()
        spot_call1 = _callinfo.Call("AA1BB")
        spot_call2 = _callinfo.Call("AA2BB")
        aggregator = _spotting.SpotAggregator(FakeDXCC())
        incoming_spot1 = _spotting.Spot(60, spot_call1, 14070000, now - 1,
            _callinfo.Call("CT1XY"), _grid.Locator("JN12aa"))
        incoming_spot2 = _spotting.Spot(60, spot_call2, 7040000, now,
            _callinfo.Call("CT2XY"), _grid.Locator("JN12aa"))
        aggregator.spot_received(incoming_spot1)
        aggregator.spot_received(incoming_spot2)

        self.assertEqual(len(aggregator.spots[spot_call1]), 1)
        self.assertEqual(len(aggregator.spots[spot_call2]), 1)

        spot1 = aggregator.spots[spot_call1][0]
        self.assertEqual(len(spot1.sources), 1)
        for source in spot1.sources:
            self.assertEqual(source.source_dxcc_info, "FakeDXCCInfo")
        self.assertEqual(spot1.frequency, 14070000)
        self.assertEqual(spot1.timeout, now - 1 + 60)
        self.assertEqual(spot1.first_seen, now - 1)
        self.assertEqual(spot1.last_seen, now - 1)

        spot2 = aggregator.spots[spot_call2][0]
        self.assertEqual(len(spot2.sources), 1)
        for source in spot2.sources:
            self.assertEqual(source.source_dxcc_info, "FakeDXCCInfo")
        self.assertEqual(spot2.frequency, 7040000)
        self.assertEqual(spot2.timeout, now + 60)
        self.assertEqual(spot2.first_seen, now)
        self.assertEqual(spot2.last_seen, now)


class TestTimeoutCleanup(unittest.TestCase):
    def test_updateSpots_shouldRemoveTimedoutSpots(self):
        now = time.time()
        spot_call = _callinfo.Call("AA1BB")
        aggregator = _spotting.SpotAggregator(FakeDXCC())
        incoming_spot = _spotting.Spot(60, spot_call, 14070000, now - 61,
            _callinfo.Call("CT1XY"), _grid.Locator("JN12aa"))
        aggregator.spot_received(incoming_spot)
        self.assertEqual(len(aggregator.spots), 1)

        aggregator.cleanup_spots()
        self.assertEqual(len(aggregator.spots), 0)

    def test_updateSpots_shouldKeepActiveSpots(self):
        now = time.time()
        spot_call = _callinfo.Call("AA1BB")
        aggregator = _spotting.SpotAggregator(FakeDXCC())
        incoming_spot = _spotting.Spot(60, spot_call, 14070000, now - 1,
            _callinfo.Call("CT1XY"), _grid.Locator("JN12aa"))
        aggregator.spot_received(incoming_spot)
        self.assertEqual(len(aggregator.spots), 1)

        aggregator.cleanup_spots()
        self.assertEqual(len(aggregator.spots), 1)


class TestLevenshteinCleanup(unittest.TestCase):
    def test_twoCalls_oneDifference_shouldAggregateToOneSpotUsingMajorityWhenChoosingFile(self):
        now = time.time()
        spot_call1 = _callinfo.Call("AA1BB")
        spot_call2 = _callinfo.Call("AA2BB")
        aggregator = _spotting.SpotAggregator(FakeDXCC())
        incoming_spot1 = _spotting.Spot(60, spot_call1, 7040000, now,
            _callinfo.Call("CT1XY"), _grid.Locator("JN12aa"))
        incoming_spot2 = _spotting.Spot(60, spot_call2, 7040000, now,
            _callinfo.Call("CT2XY"), _grid.Locator("JN12aa"))
        incoming_spot3 = _spotting.Spot(60, spot_call2, 7040000, now,
            _callinfo.Call("CT3XY"), _grid.Locator("JN12aa"))
        aggregator.spot_received(incoming_spot1)
        aggregator.spot_received(incoming_spot2)
        aggregator.spot_received(incoming_spot3)
        aggregator.cleanup_spots()

        self.assertEqual(len(aggregator.spots), 1)
        self.assertFalse(spot_call1 in aggregator.spots)
        self.assertTrue(spot_call2 in aggregator.spots)


class FakeDXCC(_dxcc.DXCC):
    def __init__(self):
        _dxcc.DXCC.__init__(self)

    def find_dxcc_info(self, call):
        return "FakeDXCCInfo"

if __name__ == '__main__': unittest.main()
