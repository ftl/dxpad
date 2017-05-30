#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, time
from PySide import QtCore, QtGui

import _spotting, _dxcc, _bandplan, _config, _windowmanager

COLOR_SPOT = QtGui.QColor(255, 120, 120)
COLOR_BACKGROUND = QtGui.QColor(200, 200, 200)
COLOR_BAND = QtGui.QColor(150, 150, 150)
COLOR_CW_PORTION = QtGui.QColor(245, 246, 206)
COLOR_DIGI_PORTION = QtGui.QColor(169, 245, 242)
COLOR_BEACON_PORTION = QtGui.QColor(245, 169, 169)
COLOR_SSB_PORTION = QtGui.QColor(169, 245, 169)
COLOR_FM_PORTION = QtGui.QColor(208, 169, 245)
COLOR_PORTION = {
	"CW": COLOR_CW_PORTION,
	"Digi": COLOR_DIGI_PORTION,
	"Baken": COLOR_BEACON_PORTION,
	"SSB": COLOR_SSB_PORTION,
	"FM": COLOR_FM_PORTION
}

class BandMap(QtCore.QObject):
	update_spots = QtCore.Signal(object)

	def __init__(self, parent = None):
		QtCore.QObject.__init__(self, parent)
		self.spots = []
		self.spotter_continents = ["EU"]

	@QtCore.Slot(object)
	def spots_received(self, spots):
		self.spots = filter(self._filter_spot, spots)
		self.update_spots.emit(self.spots)

	def _filter_spot(self, spot):
		sources_on_continent = filter(lambda source: source.source_dxcc_info and (source.source_dxcc_info.continent in self.spotter_continents, spot.sources))
		return len(sources_on_continent) > 0

class OverviewBandmap(QtGui.QWidget):	
	def __init__(self, parent = None):
		QtGui.QWidget.__init__(self, parent)
		self.setMaximumHeight(40)
		self.bandplan = _bandplan.IARU_REGION_1
		self.spots = []
		self.from_kHz = 1000.0
		self.to_kHz = 30000.0

	def paintEvent(self, event):
		painter = QtGui.QPainter()
		painter.begin(self)
		self.draw_widget(painter)
		painter.end()

	def draw_widget(self, painter):
		size = self.size()
		text_height = painter.fontMetrics().ascent() + painter.fontMetrics().descent()
		box = QtCore.QRect(0, 0, size.width(), size.height() - text_height - 2)
		pixPerKHz = box.width() / (self.to_kHz - self.from_kHz)

		painter.fillRect(box, COLOR_BACKGROUND)

		for band in self.bandplan:
			x = int((band.from_kHz - self.from_kHz) * pixPerKHz)
			w = max(1, int((band.to_kHz - band.from_kHz) * pixPerKHz))
			painter.fillRect(x, 0, w, box.height(), COLOR_BAND)
			painter.setPen(COLOR_BAND)
			painter.drawText(x, size.height() - 1, band.name)

		painter.setPen(COLOR_SPOT)
		for spot in self.spots:
			x = int((spot.frequency - self.from_kHz) * pixPerKHz)
			painter.drawLine(x, box.top(), x, box.top() + box.height() - 1)

	@QtCore.Slot(object)
	def update_spots(self, spots):
		self.spots = spots
		self.repaint()

class SingleBandBandmap(QtGui.QWidget):
	def __init__(self, parent = None):
		QtGui.QWidget.__init__(self, parent)
		self.setMaximumHeight(60)
		self.band = _bandplan.IARU_REGION_1[5]
		self.from_kHz = self.band.from_kHz
		self.to_kHz = self.band.to_kHz
		self.spots = []

	def paintEvent(self, event):
		painter = QtGui.QPainter()
		painter.begin(self)
		self.draw_widget(painter)
		painter.end()

	def draw_widget(self, painter):
		bandmap_painter = BandmapPainter(painter, self)
		bandmap_painter.draw_frequency_box(COLOR_BACKGROUND)

		for p in self.band.portions:
			if p.name in COLOR_PORTION:
				portion_color = COLOR_PORTION[p.name]
			else:
				portion_color = COLOR_BAND
			bandmap_painter.draw_portion(p.from_kHz, p.to_kHz, portion_color)

		for f in range(int(self.from_kHz), int(self.to_kHz) + 1, 5):
			bandmap_painter.draw_scale_tick(f, COLOR_BAND)
			if (f % 50) == 0:
				bandmap_painter.draw_frequency_label(f, COLOR_BAND)

		for spot in self.spots:
			bandmap_painter.mark_frequency(spot.frequency, COLOR_SPOT)

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
		bandmap_painter = BandmapPainter(painter, self)
		bandmap_painter.draw_frequency_box(COLOR_BACKGROUND)

		for f in range(int(self.from_kHz), int(self.to_kHz) + 1, 1):
			bandmap_painter.draw_scale_tick(f, COLOR_BAND)
			if (f % 10) == 0:
				bandmap_painter.draw_frequency_label(f, COLOR_BAND)

		for spot in self.spots:
			bandmap_painter.mark_frequency(spot.frequency, COLOR_SPOT)
			bandmap_painter.draw_spot_label(spot, COLOR_SPOT)

	@QtCore.Slot(object)
	def update_spots(self, spots):
		self.spots = filter(lambda spot: spot.frequency >= self.from_kHz and spot.frequency <= self.to_kHz, spots)
		self.repaint()

class BandmapPainter:
	def __init__(self, painter, widget):
		self.painter = painter
		self.widget = widget

		self.size = widget.size()
		self.text_height = painter.fontMetrics().ascent() + painter.fontMetrics().descent()
		self.frequency_box = QtCore.QRect(0, self.size.height() - 2 * self.text_height - 2 - 10, self.size.width(), self.text_height)
		self.pix_per_kHz = self.frequency_box.width() / (widget.to_kHz - widget.from_kHz)
		self.last_x_by_level = {}

	def text_width(self, text):
		return self.painter.fontMetrics().boundingRect(str(text)).width()

	def frequency_x(self, frequency):
		return int((frequency - self.widget.from_kHz) * self.pix_per_kHz)

	def draw_frequency_box(self, color):
		self.painter.fillRect(self.frequency_box, color)

	def draw_portion(self, from_kHz, to_kHz, color):
		x = self.frequency_x(from_kHz)
		width = self.frequency_x(to_kHz) - x
		rect = QtCore.QRect(x, self.frequency_box.y(), width, self.frequency_box.height())
		self.painter.fillRect(rect, color)

	def draw_scale_tick(self, frequency, color):
		x = self.frequency_x(frequency)
		y = self.frequency_box.top() + self.frequency_box.height()
		l = 10 if (frequency % 10) == 0 else 7 if (frequency % 5) == 0 else 3
		self.painter.setPen(color)
		self.painter.drawLine(x, y, x, y + l)

	def draw_frequency_label(self, frequency, color):
		text = "{:<8.1f}".format(frequency)
		frequency_x = self.frequency_x(frequency)	
		width = self.text_width(text)
		height = self.text_height
		x = frequency_x - width / 2
		y = self.size.height() - 1
		if x < 0: return
		if x + width > self.frequency_box.width(): return
		self.painter.setPen(color)
		self.painter.drawText(x, y, text) 

	def mark_frequency(self, frequency, color):
		x = self.frequency_x(frequency)
		self.painter.setPen(color)
		self.painter.drawLine(x, self.frequency_box.top(), x, self.frequency_box.top() + self.frequency_box.height() - 1)

	def draw_spot_label(self, spot, color):
		rect = self._find_spot_rect(spot)
		self.painter.setPen(color)
		self.painter.drawRect(rect)
		self.painter.drawText(rect.x() + 2, rect.y() + self.text_height, str(spot.call))

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
		single_band = SingleBandBandmap(self)
		detail = DetailedBandmap(self)

		vbox = QtGui.QVBoxLayout()
		vbox.addWidget(detail)
		vbox.addWidget(single_band)
		vbox.addWidget(overview)

		self.setLayout(vbox)

		self.bandmap.update_spots.connect(overview.update_spots)
		self.bandmap.update_spots.connect(single_band.update_spots)
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
	dxcc.load()
	aggregator = _spotting.SpotAggregator(dxcc)
	bandmap = BandMap()

	wid = BandmapWindow(bandmap)
	wid.resize(1000, 300)
	wid.show()

	aggregator.update_spots.connect(bandmap.spots_received)
	bandmap.update_spots.connect(print_bandmap)

	clusters = config.clusters
	spotting_file = None #"rbn.txt"
	aggregator.start_spotting(clusters, spotting_file)

	result = app.exec_()
	
	aggregator.stop_spotting()
	sys.exit(result)
