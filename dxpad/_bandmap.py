#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, time
from PySide import QtCore, QtGui

import _spotting, _dxcc, _bandplan, _config, _windowmanager

COLOR_SPOT = QtGui.QColor(255, 120, 120)
COLOR_BACKGROUND = QtGui.QColor(200, 200, 200)
COLOR_BAND = QtGui.QColor(150, 150, 150)

class Spot:
	def __init__(self, call, frequency):
		self.call = call
		self.frequency = frequency
		self.sources = set([])
		self.lastseen = 0

	def __str__(self):
		return "{0:<10} on {1:>8.1f} kHz, age {2:3.0f}, sources: {3:>2.0f}".format(self.call, self.frequency, time.time() - self.lastseen, len(self.sources))


class BandMap(QtCore.QObject):
	update_spots = QtCore.Signal(object)

	def __init__(self, dxcc, parent = None):
		QtCore.QObject.__init__(self, parent)
		self.dxcc = dxcc
		self.spots = {}
		self.spotter_continents = ["EU"]
		self.timer = QtCore.QTimer(self)
		self.timer.timeout.connect(self.tick)
		self.timer.start(1000)

	@QtCore.Slot(object)
	def spot_received(self, incoming_spot):
		if not self._filter_spot(incoming_spot): return

		if incoming_spot.call in self.spots:
			spots_by_call = self.spots[incoming_spot.call]
			spot = None
			for s in spots_by_call:
				if abs(s.frequency - incoming_spot.frequency) <= 2:
					spot = s
					break

			if not spot:
				spot = Spot(incoming_spot.call, incoming_spot.frequency)
				spot.sources.add((incoming_spot.source_call, incoming_spot.source_grid))
				spot.lastseen = incoming_spot.time
				spots_by_call.append(spot)
			else:
				spot.sources.add((incoming_spot.source_call, incoming_spot.source_grid))
				spot.frequency = (spot.frequency + incoming_spot.frequency) / 2
				spot.lastseen = incoming_spot.time

		else:
			spot = Spot(incoming_spot.call, incoming_spot.frequency)
			spot.sources.add((incoming_spot.source_call, incoming_spot.source_grid))
			spot.lastseen = incoming_spot.time
			spots_by_call = [spot]

		self.spots[incoming_spot.call] = spots_by_call

	def _filter_spot(self, spot):
		dxcc_info = self.dxcc.find_dxcc_info(spot.source_call)
		if not dxcc_info: return False
		if not dxcc_info.continent in self.spotter_continents: return False
		return True

	@QtCore.Slot()
	def tick(self):
		now = time.time()
		spots = {}
		bandmap = []
		for call in self.spots.keys():
			spots_by_call = filter(lambda spot: now - spot.lastseen <= 60, self.spots[call])
			if len(spots_by_call) > 0:
				spots[call] = spots_by_call
				bandmap.extend(spots_by_call)

		self.spots = spots
		bandmap = sorted(bandmap, key= lambda spot: spot.frequency)

		self.update_spots.emit(bandmap)


class OverviewBandmap(QtGui.QWidget):	
	def __init__(self, parent = None):
		QtGui.QWidget.__init__(self, parent)
		self.setMaximumHeight(40)
		self.bandplan = _bandplan.IARU_REGION_1
		self.spots = []
		self.fromKHz = 1000.0
		self.toKHz = 30000.0

	def paintEvent(self, event):
		painter = QtGui.QPainter()
		painter.begin(self)
		self.draw_widget(painter)
		painter.end()

	def draw_widget(self, painter):
		size = self.size()
		text_height = painter.fontMetrics().ascent() + painter.fontMetrics().descent()
		box = QtCore.QRect(0, 0, size.width(), size.height() - text_height - 2)
		pixPerKHz = box.width() / (self.toKHz - self.fromKHz)

		painter.fillRect(box, COLOR_BACKGROUND)

		for band in self.bandplan:
			x = int((band.from_kHz - self.fromKHz) * pixPerKHz)
			w = max(1, int((band.to_kHz - band.from_kHz) * pixPerKHz))
			painter.fillRect(x, 0, w, box.height(), COLOR_BAND)
			painter.setPen(COLOR_BAND)
			painter.drawText(x, size.height() - 1, band.name)

		painter.setPen(COLOR_SPOT)
		for spot in self.spots:
			x = int((spot.frequency - self.fromKHz) * pixPerKHz)
			painter.drawLine(x, box.top(), x, box.top() + box.height() - 1)

	@QtCore.Slot(object)
	def update_spots(self, spots):
		self.spots = spots
		self.repaint()

class DetailedBandmap(QtGui.QWidget):
	def __init__(self, parent = None):
		QtGui.QWidget.__init__(self, parent)
		self.spots = []
		self.from_kHz = 14000.0
		self.to_kHz = 14100.0

	def paintEvent(self, event):
		painter = QtGui.QPainter()
		painter.begin(self)
		self.draw_widget(painter)
		painter.end()

	def draw_widget(self, painter):
		bandmap_painter = DetailedBandmapPainter(painter, self)
		bandmap_painter.draw_frequency_box(COLOR_BACKGROUND)

		bandmap_painter.draw_left_label("{:<8.1f} kHz".format(self.from_kHz), COLOR_BAND)
		bandmap_painter.draw_right_label("{:>8.1f} kHz".format(self.to_kHz), COLOR_BAND)

		for spot in self.spots:
			bandmap_painter.mark_frequency(spot.frequency, COLOR_SPOT)
			bandmap_painter.draw_spot_label(spot, COLOR_SPOT)

	@QtCore.Slot(object)
	def update_spots(self, spots):
		self.spots = filter(lambda spot: spot.frequency >= self.from_kHz and spot.frequency <= self.to_kHz, spots)
		self.repaint()

class DetailedBandmapPainter:
	def __init__(self, painter, widget):
		self.painter = painter
		self.widget = widget

		self.size = widget.size()
		self.text_height = painter.fontMetrics().ascent() + painter.fontMetrics().descent()
		self.frequency_box = QtCore.QRect(0, self.size.height() - 2 * self.text_height - 2, self.size.width(), self.text_height)
		self.pix_per_kHz = self.frequency_box.width() / (widget.to_kHz - widget.from_kHz)
		self.last_x_by_level = {}

	def text_width(self, text):
		return self.painter.fontMetrics().boundingRect(text).width()

	def frequency_x(self, frequency):
		return int((frequency - self.widget.from_kHz) * self.pix_per_kHz)

	def draw_frequency_box(self, color):
		self.painter.fillRect(self.frequency_box, color)

	def draw_left_label(self, text, color):
		self.painter.setPen(color)
		self.painter.drawText(0, self.size.height() - 1, text)

	def draw_right_label(self, text, color):
		self.painter.setPen(color)
		self.painter.drawText(self.size.width() - self.text_width(text), self.size.height() - 1, text)

	def mark_frequency(self, frequency, color):
		x = self.frequency_x(frequency)
		self.painter.setPen(color)
		self.painter.drawLine(x, self.frequency_box.top(), x, self.frequency_box.top() + self.frequency_box.height() - 1)

	def draw_spot_label(self, spot, color):
		rect = self._find_spot_rect(spot)
		self.painter.setPen(color)
		self.painter.drawRect(rect)
		self.painter.drawText(rect.x() + 2, rect.y() + self.text_height, spot.call)

	def _find_spot_rect(self, spot):
		frequency_x = self.frequency_x(spot.frequency)
		width = self.text_width(spot.call) + 4
		height = self.text_height + 4

		x = max(0, min(frequency_x - width / 2, self.frequency_box.width() - width - 1))
		level = self._find_free_level(x, width)
		y = self.frequency_box.top() - 1 - (level  + 1) * (height + 2)

		return QtCore.QRect(x, y, width, height)

	def _find_free_level(self, x, width):
		level = 0
		last_x = sys.maxint
		while last_x >= x:
			if level in self.last_x_by_level:
				last_x = self.last_x_by_level[level]
			else:
				last_x = x - 1
			if last_x >= x:
				level += 1
			else:
				self.last_x_by_level[level] = x + width + 2
		return level


class BandmapWindow(_windowmanager.ManagedWindow):
	def __init__(self, bandmap, parent = None):
		_windowmanager.ManagedWindow.__init__(self, parent)
		self.bandmap = bandmap	

		self.setObjectName("bandmap")
		self.setWindowTitle("Bandmap")
		self.resize(1000, 300)

		overview = OverviewBandmap(self)
		detail = DetailedBandmap(self)

		vbox = QtGui.QVBoxLayout()
		vbox.addWidget(detail)
		vbox.addWidget(overview)

		self.setLayout(vbox)

		self.bandmap.update_spots.connect(overview.update_spots)
		self.bandmap.update_spots.connect(detail.update_spots)


@QtCore.Slot(object)
def print_bandmap(bandmap):
	print "Bandmap at {}:".format(time.strftime("%H:%M:%SZ", time.gmtime(time.time())))
	print "\n".join(map(lambda spot: str(spot), bandmap))
	print ""

if __name__ == "__main__":
	app = QtGui.QApplication(sys.argv)

	config = _config.load_config()

	dxcc = _dxcc.DXCC()
	dxcc.load_from_file("cty.dat")
	bandmap = BandMap(dxcc)

	wid = BandmapWindow(bandmap)
	wid.resize(1000, 300)
	wid.show()

	bandmap.update_spots.connect(print_bandmap)

	clusters = config.clusters
	spotting_file = None #"rbn.txt"

	spotting_threads = []
	for c in clusters:
		st = _spotting.SpottingThread.telnet(c.host, c.port, c.user, c.password)
		st.spot_received.connect(bandmap.spot_received)
		st.start()
		spotting_threads.append(st)

	if spotting_file:
		st = _spotting.SpottingThread.textfile(spotting_file)
		st.spot_received.connect(bandmap.spot_received)
		st.start()
		spotting_threads.append(st)

	result = app.exec_()
	
	for st in spotting_threads:
		st.stop()
		st.wait()

	sys.exit(result)
