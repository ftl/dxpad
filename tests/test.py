#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, os, unittest
sys.path.insert(0, os.path.abspath('..'))

import dxpad._location as _location
import dxpad._grid as _grid
import dxpad._notepad as _notepad
import dxpad._callinfo as _callinfo

class TestLatLon(unittest.TestCase):
	def test_neighbours_somewhere_in_the_middle(self):
		lat_lon = _location.LatLon(48, 10)
		self.assertEqual( lat_lon.neighbours(), 
			set([
				_location.LatLon(47, 8),
				_location.LatLon(47, 10),
				_location.LatLon(47, 12),
				_location.LatLon(48, 8),
				_location.LatLon(48, 12),
				_location.LatLon(49, 8),
				_location.LatLon(49, 10),
				_location.LatLon(49, 12)
			]) 
		)

	def test_neighbours_left_end(self):
		lat_lon = _location.LatLon(48, -180)
		self.assertEqual( lat_lon.neighbours(), 
			set([
				_location.LatLon(47, 178),
				_location.LatLon(47, -180),
				_location.LatLon(47, -178),
				_location.LatLon(48, 178),
				_location.LatLon(48, -178),
				_location.LatLon(49, 178),
				_location.LatLon(49, -180),
				_location.LatLon(49, -178)
			]) 
		)

	def test_neighbours_right_end(self):
		lat_lon = _location.LatLon(48, 180)
		self.assertEqual( lat_lon.neighbours(), 
			set([
				_location.LatLon(47, 178),
				_location.LatLon(47, 180),
				_location.LatLon(47, -178),
				_location.LatLon(48, 178),
				_location.LatLon(48, -178),
				_location.LatLon(49, 178),
				_location.LatLon(49, 180),
				_location.LatLon(49, -178)
			]) 
		)

	def test_neighbours_top_end(self):
		lat_lon = _location.LatLon(90, 10)
		self.assertEqual( lat_lon.neighbours(), 
			set([
				_location.LatLon(89, 8),
				_location.LatLon(89, 10),
				_location.LatLon(89, 12),
				_location.LatLon(90, 8),
				_location.LatLon(90, 12),
			]) 
		)

	def test_neighbours_bottom_end(self):
		lat_lon = _location.LatLon(-90, 10)
		self.assertEqual( lat_lon.neighbours(), 
			set([
				_location.LatLon(-89, 8),
				_location.LatLon(-89, 10),
				_location.LatLon(-89, 12),
				_location.LatLon(-90, 8),
				_location.LatLon(-90, 12),
			]) 
		)

	def test_neighbours_center(self):
		lat_lon = _location.LatLon(0, 0)
		self.assertEqual( lat_lon.neighbours(), 
			set([
				_location.LatLon(-1, -2),
				_location.LatLon(-1, 0),
				_location.LatLon(-1, 2),
				_location.LatLon(0, -2),
				_location.LatLon(0, 2),
				_location.LatLon(1, -2),
				_location.LatLon(1, 0),
				_location.LatLon(1, 2)
			]) 
		)

	def test_hash_int(self):
		hashes = set()
		conflicts = []
		for lat in range(-90, 91):
			for lon in range(-180, 180):
				lat_lon = _location.LatLon(lat, lon)
				h = hash(lat_lon)
				if lat_lon in hashes:
					print "conflict {}".format(lat_lon)
					conflicts.append(lat_lon)
				else:
					hashes.add(lat_lon)
		self.assertEqual(len(conflicts), 0, "{} conflicting {}".format(len(hashes), len(conflicts)))

class TestLocatorHeatmap1(unittest.TestCase):
	def test_left_end_add_once(self):
		self.maxDiff = None
		heatmap = _grid.LocatorHeatmap1(max_heat = 20, heat_propagation = 0.5, heat_threshold = 5)
		heatmap.add(_grid.Locator("AN00aa"))
		self.assertItemsEqual( heatmap.heatmap.keys(),
			[
				_location.LatLon(41, 178),
				_location.LatLon(41, -180),
				_location.LatLon(41, -178),
				_location.LatLon(40, 178),
				_location.LatLon(40, -180),
				_location.LatLon(40, -178),
				_location.LatLon(39, 178),
				_location.LatLon(39, -180),
				_location.LatLon(39, -178)
			] 
		)

	def test_left_end_add_twice(self):
		self.maxDiff = None
		heatmap = _grid.LocatorHeatmap1(max_heat = 20, heat_propagation = 0.5, heat_threshold = 9)
		heatmap.add(_grid.Locator("AN00aa"))
		heatmap.add(_grid.Locator("AN00aa"))
		#print "\n".join(map(lambda l: str(l), heatmap.heatmap.keys()))
		self.assertItemsEqual( heatmap.heatmap.keys(),
			[
				_location.LatLon(42, 176),
				_location.LatLon(42, 178),
				_location.LatLon(42, -180),
				_location.LatLon(42, -178),
				_location.LatLon(42, -176),

				_location.LatLon(41, 176),
				_location.LatLon(41, 178),
				_location.LatLon(41, -180),
				_location.LatLon(41, -178),
				_location.LatLon(41, -176),
				
				_location.LatLon(40, 176),
				_location.LatLon(40, 178),
				_location.LatLon(40, -180),
				_location.LatLon(40, -178),
				_location.LatLon(40, -176),
				
				_location.LatLon(39, 176),
				_location.LatLon(39, 178),
				_location.LatLon(39, -180),
				_location.LatLon(39, -178),
				_location.LatLon(39, -176),
				
				_location.LatLon(38, 176),
				_location.LatLon(38, 178),
				_location.LatLon(38, -180),
				_location.LatLon(38, -178),
				_location.LatLon(38, -176)
			] 
		)

class TestNotedQsos(unittest.TestCase):
	def setUp(self):
		self.qsos = _notepad.NotedQsos()
	def assertInQso(self, line):
		self.assertTrue(self.qsos.is_in_qso(line))
	def assertNotInQso(self, line):
		self.assertFalse(self.qsos.is_in_qso(line))
	def assertQsosInOrder(self):
		for i in range(0, len(self.qsos) - 1):
			self.assertTrue(self.qsos[i].end < self.qsos[i + 1].start)

	def test_insert_single_qso_should_indicate_in_qso(self):
		self.assertNotInQso(10)

		self.qsos.insert_qso(10)
		
		self.assertNotInQso(9)
		self.assertInQso(10)
		self.assertNotInQso(11)

	def test_insert_two_qsos_should_insert_in_order(self):
		for i in range(20, 10, -2):
			self.qsos.insert_qso(i)
		self.assertEqual(5, len(self.qsos))
		self.assertQsosInOrder()

	def test_remove_qso(self):
		for i in range(20, 10, -2):
			self.qsos.insert_qso(i)
		self.qsos.remove_qso(16)

		self.assertEqual(4, len(self.qsos))

	def test_insert_qso_twice_should_ignore_second_attempt(self):
		self.qsos.insert_qso(10)
		self.qsos.insert_qso(10)

		self.assertEqual(1, len(self.qsos))

	def test_get_qso_for_line(self):
		self.qsos.insert_qso(10)

		self.assertEqual(None, self.qsos.get_qso(9))
		self.assertEqual(10, self.qsos.get_qso(10).start)
		self.assertEqual(None, self.qsos.get_qso(11))

	def test_move_qso_start_up(self):
		self.qsos.insert_qso(10)
		self.qsos.move_qso_start(8)

		qso = self.qsos.get_qso(8)
		self.assertEqual(8, qso.start)
		self.assertEqual(10, qso.end)
		self.assertEqual(qso, self.qsos.get_qso(9))
		self.assertEqual(qso, self.qsos.get_qso(10))

	def test_move_qso_start_down(self):
		self.qsos.insert_qso(10)
		self.qsos.move_qso_start(5)
		self.qsos.move_qso_start(8)

		qso = self.qsos.get_qso(8)
		self.assertEqual(8, qso.start)
		self.assertEqual(10, qso.end)

		self.assertNotInQso(5)
		self.assertNotInQso(6)
		self.assertNotInQso(7)

	def test_insert_qso_by_moving_start_after_last_qso(self):
		self.qsos.insert_qso(10)
		self.qsos.move_qso_start(12)

		self.assertEqual(2, len(self.qsos))
		self.assertNotEqual(self.qsos.get_qso(10), self.qsos.get_qso(12))

	def test_move_qso_end_down(self):
		self.qsos.insert_qso(10)
		self.qsos.move_qso_end(12)

		qso = self.qsos.get_qso(12)
		self.assertEqual(10, qso.start)
		self.assertEqual(12, qso.end)
		self.assertEqual(qso, self.qsos.get_qso(10))
		self.assertEqual(qso, self.qsos.get_qso(11))

class TestCall(unittest.TestCase):
	def assertCall(self, call, prefix, base_call, suffix, working_condition):
		self.assertEquals(prefix, call.prefix)
		self.assertEquals(base_call, call.base_call)
		self.assertEquals(suffix, call.suffix)
		self.assertEquals(working_condition, call.working_condition)

	def test_find_all(self):
		calls = _callinfo.Call.find_all("DL3NEY W1AW 9A1AA EA6/DJ9MH VE3/DL1NEO/9 DL3NY/HA2 DF2NK/p VK7/DK6MP/9/p", lambda m: m.group())
		self.assertItemsEqual(["DL3NEY", "W1AW", "9A1AA", "EA6/DJ9MH", "VE3/DL1NEO/9", "DL3NY/HA2", "DF2NK/p", "VK7/DK6MP/9/p"], calls)

	def test_base_call(self):
		self.assertCall(_callinfo.Call("DL3NEY"), None, "DL3NEY", None, None)

	def test_base_call_with_prefix(self):
		self.assertCall(_callinfo.Call("EA6/DL3NEY"), "EA6", "DL3NEY", None, None)

	def test_base_call_with_working_condition(self):
		self.assertCall(_callinfo.Call("DL3NEY/p"), None, "DL3NEY", None, "P")

	def test_base_call_with_suffix(self):
		self.assertCall(_callinfo.Call("DL3NEY/KP4"), None, "DL3NEY", "KP4", None)

	def test_base_call_with_suffix_and_working_condition(self):
		self.assertCall(_callinfo.Call("DL3NEY/KP4/MM"), None, "DL3NEY", "KP4", "MM")

	def test_base_call_with_prefix_and_working_condition(self):
		self.assertCall(_callinfo.Call("EA8/DL3NEY/MM"), "EA8", "DL3NEY", None, "MM")

	def test_base_call_with_prefix_and_suffix(self):
		self.assertCall(_callinfo.Call("WB3/DL3NEY/8"), "WB3", "DL3NEY", "8", None)

	def test_base_call_with_prefix_and_suffix_and_working_condition(self):
		self.assertCall(_callinfo.Call("WB3/DL3NEY/8/p"), "WB3", "DL3NEY", "8", "P")

if __name__ ==  '__main__': unittest.main()
