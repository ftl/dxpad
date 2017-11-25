#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
import os

from PySide import QtCore, QtGui, QtSvg

from . import _sun, _location, _grid, _dxcc, _bandmap, _bandplan, _spotting, \
              _config, _callinfo, _windowmanager


"""
show_itu()
hide_itu()
show_cq()
hide_cq()

highlight_location(LatLon, scale, value)
clear_location(LatLon)

show_connection(LatLon, LatLon)
hide_connection()

add_marker(LatLon, kind)
remove_marker(LatLon, kind)
"""

HEAT_COLORS = [(0, 0, 255), (0, 255, 255), (0, 255, 0), (255, 255, 0), 
               (255, 0, 0)]

class LocatorHeatmap:
    MAX_HEAT = 1.0
    def __init__(self, cell_width = 2, cell_height = 1):
        self.heatmap = {}
        self.cell_width = cell_width
        self.cell_height = cell_height

    def add(self, locator, heat, add = float.__add__):
        coordinates = self._to_coordinates(locator)
        self._add_heat(coordinates, heat, add)

    def _to_coordinates(self, locator):
        latlon = locator.to_lat_lon()
        return _location.LatLon(
            int(latlon.lat) - int(latlon.lat) % self.cell_height, 
            int(latlon.lon) - int(latlon.lon) % self.cell_width)

    def _add_heat(self, coordinates, heat, add):
        current_heat = self._heat(coordinates)
        new_heat = min(add(current_heat, heat), self.MAX_HEAT)
        self.heatmap[coordinates] = new_heat
        return new_heat

    def _heat(self, coordinates):
        if not coordinates in self.heatmap: return 0.0
        return self.heatmap[coordinates]


class SpotterContinentFilter:
    def __init__(self, continents = []):
        self.continents = continents

    def filter_spot(self, spot):
        return [
            source for source in spot.sources 
            if source.source_dxcc_info 
                and (source.source_dxcc_info.continent in self.continents)]

    def spot_locators(self, spot):
        if not(spot.dxcc_info): return []
        return [(_grid.Locator.from_lat_lon(spot.dxcc_info.latlon), 0.1)]

    def add_heat(self, a, b):
        return a + b

class SpotterFilter:
    def __init__(self, call = None):
        self.call = call

    def filter_spot(self, spot):
        if not self.call: return False
        return len([source for source in spot.sources
                    if self.call.base_call == source.source_call.base_call]) > 0

    def spot_locators(self, spot):
        if not(spot.dxcc_info): return []
        return [(_grid.Locator.from_lat_lon(spot.dxcc_info.latlon), 0.5)]

    def add_heat(self, a, b):
        return a + b

class ReceivingCallFilter:
    MAX_SNR = 30.0
    def __init__(self, call = None):
        self.call = call

    def filter_spot(self, spot):
        if not self.call: return False
        return self.call.base_call == spot.call.base_call

    def spot_locators(self, spot):
        def to_grid_heat_tuple(source):
            if hasattr(source, "snr"):
                heat = source.snr / self.MAX_SNR
            else:
                heat = 0.1
            if source.source_grid:
                grid = source.source_grid
            else:
                grid = _grid.Locator.from_lat_lon(
                    source.source_dxcc_info.latlon)
            return (grid, heat)
        return [to_grid_heat_tuple(source) for source in spot.sources]

    def add_heat(self, a, b):
        return (a + b) / 2.0


class Map(QtCore.QObject):
    changed = QtCore.Signal()

    def __init__(
            self, spot_cell_width = 5, spot_cell_height = 5, parent = None):
        QtCore.QObject.__init__(self, parent)
        self.spot_cell_width = spot_cell_width
        self.spot_cell_height = spot_cell_height
        self.map_visible = True
        self.grid_visible = True
        self.grayline_visible = True
        self.own_locator = None
        self.destination_locator = None
        self.locator_heatmap = LocatorHeatmap(
            cell_width = self.spot_cell_width, 
            cell_height = self.spot_cell_height)
        self.band = _bandplan.NO_BAND
        self.spot_filters = [
            SpotterContinentFilter(),
            ReceivingCallFilter(),
            ReceivingCallFilter(),
            SpotterFilter()]
        self.spot_filter = self.spot_filters[0]

    @QtCore.Slot(bool)
    def show_map(self, state):
        self.map_visible = state
        self.changed.emit()

    @QtCore.Slot(bool)
    def show_grid(self, state):
        self.grid_visible = state
        self.changed.emit()

    @QtCore.Slot(bool)
    def show_grayline(self, state):
        self.grayline_visible = state
        self.changed.emit()

    @QtCore.Slot(object)
    def set_own_call(self, call):
        self.spot_filters[1].call = call
        self.changed.emit()

    @QtCore.Slot(object)
    def set_own_locator(self, locator):
        self.own_locator = locator
        self.changed.emit()

    @QtCore.Slot(object)
    def set_destination_locator(self, locator):
        self.destination_locator = locator
        self.changed.emit()

    @QtCore.Slot(object)
    def clear_destination_locator(self):
        self.destination_locator = None
        self.changed.emit()

    @QtCore.Slot(object)
    def select_continents(self, continents):
        self.spot_filters[0].continents = continents
        self.changed.emit()

    @QtCore.Slot()
    def show_spots_received_on_selected_continents(self):
        self.spot_filter = self.spot_filters[0]
        self.changed.emit()

    @QtCore.Slot(object)
    def select_call(self, call):
        self.spot_filters[2].call = call
        self.spot_filters[3].call = call
        self.changed.emit()

    def selected_call(self):
        return self.spot_filters[2].call

    @QtCore.Slot(object)
    def select_band(self, band):
        self.band = band
        self.changed.emit()

    @QtCore.Slot()
    def show_spots_receiving_own_call(self):
        self.spot_filter = self.spot_filters[1]
        self.changed.emit()

    @QtCore.Slot()
    def show_spots_receiving_selected_call(self):
        self.spot_filter = self.spot_filters[2]
        self.changed.emit()

    @QtCore.Slot()
    def show_spots_from_selected_call(self):
        self.spot_filter = self.spot_filters[3]
        self.changed.emit()

    @QtCore.Slot(object)
    def highlight_spots(self, spots):
        locator_heatmap = LocatorHeatmap(
            cell_width = self.spot_cell_width, 
            cell_height = self.spot_cell_height)
        filtered_spots = list(
            filter(self.spot_filter.filter_spot, 
                list(filter(self._in_selected_band, spots))))
        for spot in filtered_spots:
            for locator, heat in self.spot_filter.spot_locators(spot):
                locator_heatmap.add(locator, heat, self.spot_filter.add_heat)
        self.locator_heatmap = locator_heatmap
        self.changed.emit()

    def _in_selected_band(self, spot):
        return self.band.contains(spot.frequency)


class MapWidget(QtGui.QWidget):
    def __init__(self, map, parent = None):
        QtGui.QWidget.__init__(self, parent)
        self.map = map
        self.map.changed.connect(self.repaint)
        self.world_graphic = QtSvg.QGraphicsSvgItem(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "map.svg"))

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        self.draw_widget(painter)
        painter.end()

    def sizeHint(self):
        return self._size_in_ratio()

    def _size_in_ratio(self):
        size = self.size()
        height_for_width = int(size.width() / 2)
        width_for_height = size.height() * 2
        if height_for_width <= size.height(): 
            return QtCore.QSize(size.width(), height_for_width)
        else: 
            return QtCore.QSize(width_for_height, size.height())

    def draw_widget(self, painter):
        size = self._size_in_ratio()
        box = QtCore.QRect(
            (self.size().width() - size.width()) / 2, 
            (self.size().height() - size.height()) / 2, 
            size.width(), size.height())

        painter.translate(box.x(), box.y())
        painter.scale(float(size.width() / 360.0), float(size.height() / 180.0))
        if self.map.map_visible:
            self._draw_map(painter)

        painter.translate(180, 90)
        painter.scale(1, -1)
        if self.map.grid_visible:
            self._draw_grid(painter)
        if self.map.grayline_visible:
            self._draw_grayline(painter)
        self._draw_locator_heatmap(painter)
        self._draw_own_locator(painter)
        self._draw_destination(painter)

    def _draw_map(self, painter):
        self.world_graphic.paint(painter, QtGui.QStyleOptionGraphicsItem())

    def _draw_grid(self, painter):
        painter.setOpacity(0.5)
        painter.setPen(QtGui.QColor(100, 100, 100))
        for lat in range(-80, 90, 10):
            painter.drawLine(-180, lat, 180, lat)
        for lon in range(-160, 180, 20):
            painter.drawLine(lon, -90, lon, 90)

    def _draw_grayline(self, painter):
        polygon = QtGui.QPolygonF()
        for p in _sun.calculate_day_night_terminator(time.time()):
            polygon.append(QtCore.QPointF(p[1], p[0]))

        painter.setOpacity(0.3)        
        painter.setPen(QtGui.QColor(0, 0, 0))
        painter.setBrush(QtGui.QColor(0, 0, 0))
        painter.drawPolygon(polygon)

    def _draw_own_locator(self, painter):
        self._draw_highlighted_locator(
            painter, self.map.own_locator, QtGui.QColor(255, 0, 0))

    def _draw_destination(self, painter):
        self._draw_highlighted_locator(
            painter, self.map.destination_locator, QtGui.QColor(0, 0, 255))
        self._draw_direct_line(
            painter, self.map.own_locator, self.map.destination_locator, 
            QtGui.QColor(0, 0, 255))

    def _draw_highlighted_locator(
            self, painter, locator, color = QtGui.QColor(0, 0, 0), 
            opacity = 1):
        if not locator: return
        r = 1.0
        w = 1.0
        latlon = locator.to_lat_lon()
        top_left = QtCore.QPointF(latlon.lon - r, latlon.lat - r)
        top_right = QtCore.QPointF(latlon.lon + r, latlon.lat - r)
        bottom_left = QtCore.QPointF(latlon.lon - r, latlon.lat + r)
        bottom_right = QtCore.QPointF(latlon.lon + r, latlon.lat + r)
        painter.setOpacity(opacity)
        pen = QtGui.QPen(color)
        pen.setWidthF(w)
        painter.setPen(pen)
        painter.drawLine(top_left, bottom_right)
        painter.drawLine(bottom_left, top_right)

    def _draw_direct_line(
            self, painter, source_locator, destination_locator, 
            color = QtGui.QColor(0, 0, 0), opacity = 1):
        if not(source_locator and destination_locator): return
        source_latlon = source_locator.to_lat_lon()
        destination_latlon = destination_locator.to_lat_lon()
        p1 = QtCore.QPointF(source_latlon.lon, source_latlon.lat)
        p2 = QtCore.QPointF(destination_latlon.lon, destination_latlon.lat)
        painter.setOpacity(opacity)
        pen = QtGui.QPen(color)
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.drawLine(p1, p2)        

    def _draw_locator_field(
            self, painter, locator, color = QtGui.QColor(255, 0, 0), 
            opacity = 1):
        if not locator: return
        latlon = locator.to_lat_lon()
        precision = len(str(locator))
        if precision >= 6:
            width = 0.5 # 1/12 is too small
            height = 0.25 # 1/24 is too small
        elif precision >= 4:
            width = 2
            height = 1
        else:
            width = 20
            height = 10
        self._draw_lat_lon(painter, latlon, width, height, color, opacity)

    def _draw_locator_heatmap(self, painter):
        heatmap = self.map.locator_heatmap
        for latlon in heatmap.heatmap:
            heat = self.map.locator_heatmap.heatmap[latlon]
            self._draw_lat_lon(
                painter, latlon, width = heatmap.cell_width, 
                height = heatmap.cell_height, color = self._heat_color(heat), 
                opacity = 0.4)

    def _draw_lat_lon(
            self, painter, latlon, width = 2, height = 1, 
            color = QtGui.QColor(255, 0, 0), opacity = 1):
        rect = QtCore.QRectF(latlon.lon, latlon.lat, width, height)
        painter.setOpacity(opacity)
        painter.fillRect(rect, color)

    def _heat_color(self, heat):
        adapted_heat = float(heat * (len(HEAT_COLORS) - 1.0))
        color_index = int(adapted_heat)
        lower = HEAT_COLORS[color_index]
        upper = HEAT_COLORS[min(color_index + 1, len(HEAT_COLORS) - 1)]
        p = adapted_heat - color_index
        result = []
        for i in range(0, 3):
            result.append((1 - p) * lower[i] + p * upper[i])
        return QtGui.QColor(result[0], result[1], result[2])


class MapWindow(_windowmanager.ManagedWindow):
    def __init__(self, map, parent = None):
        _windowmanager.ManagedWindow.__init__(self, parent)
        self.setObjectName("map")
        self.setWindowTitle("Map")
        self.resize(1200, 600)
        self.map = map
        self.map_widget = MapWidget(map)
        self.map.changed.connect(self._map_changed)

        show_spots_received_on_selected_continents = QtGui.QRadioButton()
        show_spots_received_on_selected_continents.setText(
            "Empfangen in " + ", ".join(self.map.spot_filters[0].continents))
        show_spots_received_on_selected_continents.setChecked(True)
        show_spots_received_on_selected_continents.clicked.connect(
            self.map.show_spots_received_on_selected_continents)

        show_spots_receiving_own_call = QtGui.QRadioButton()
        show_spots_receiving_own_call.setText("Meine Reichweite")
        show_spots_receiving_own_call.setChecked(False)
        show_spots_receiving_own_call.clicked.connect(
            self.map.show_spots_receiving_own_call)

        self.show_spots_receiving_selected_call = QtGui.QRadioButton()
        self.show_spots_receiving_selected_call.setText("Reichweite von")
        self.show_spots_receiving_selected_call.setChecked(False)
        self.show_spots_receiving_selected_call.clicked.connect(
            self.map.show_spots_receiving_selected_call)

        self.show_spots_from_selected_call = QtGui.QRadioButton()
        self.show_spots_from_selected_call.setText("Empfangen von")
        self.show_spots_from_selected_call.setChecked(False)
        self.show_spots_from_selected_call.clicked.connect(
            self.map.show_spots_from_selected_call)


        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(show_spots_received_on_selected_continents)
        hbox.addWidget(show_spots_receiving_own_call)
        hbox.addWidget(self.show_spots_receiving_selected_call)
        hbox.addWidget(self.show_spots_from_selected_call)

        vbox = QtGui.QVBoxLayout()
        vbox.addLayout(hbox)
        vbox.addWidget(self.map_widget)

        self.setLayout(vbox)

    def _map_changed(self):
        selected_call = self.map.selected_call()
        if selected_call:
            self.show_spots_receiving_selected_call.setText("Reichweite von {}"
                .format(selected_call))
            self.show_spots_from_selected_call.setText("Empfangen von {}"
                .format(selected_call))
        else:
            self.show_spots_receiving_selected_call.setText("Reichweite von")
            self.show_spots_from_selected_call.setText("Empfangen von")


def highlight_spot(map_widget):    
    map_widget.locator_heatmap.add(_grid.Locator("AN00aa"))
    map_widget.locator_heatmap.add(_grid.Locator("CN50kk"))
    map_widget.repaint()


def main(args):
    app = QtGui.QApplication(args)

    config = _config.load_config()

    for arg in args[1:]:
        map_widget.highlight_locator(_grid.Locator(arg))

    dxcc = _dxcc.DXCC()
    dxcc.load()
    aggregator = _spotting.SpotAggregator(dxcc)

    spot_cleanup_timer = QtCore.QTimer()
    spot_cleanup_timer.timeout.connect(aggregator.cleanup_spots)
    spot_cleanup_timer.start(1000)
    
    map = Map()
    map.set_own_locator(config.locator)
    map.set_destination_locator(_grid.Locator("EM42kt"))
    map.select_call(_callinfo.Call("K1TTT")) #config.call)
    map.select_continents([dxcc.find_dxcc_info(config.call).continent])
    map.select_band(_bandplan.IARU_REGION_1[4])
    aggregator.update_spots.connect(map.highlight_spots)

    win = MapWindow(map)
    win.show()

    st = _spotting.SpottingThread.textfile("rbn.txt")
    st.spot_received.connect(aggregator.spot_received)
    st.start()

    result = app.exec_()

    st.stop()
    st.wait()

    sys.exit(result)
