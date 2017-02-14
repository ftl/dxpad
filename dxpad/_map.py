#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, time, os
from PySide import QtCore, QtGui, QtSvg

import _sun, _location, _grid, _dxcc, _bandmap, _spotting, _config, _windowmanager


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

HEAT_COLORS = [(0, 0, 255), (0, 255, 255), (0, 255, 0), (255, 255, 0), (255, 0, 0)]

class Map(QtCore.QObject):
    changed = QtCore.Signal()

    def __init__(self, parent = None):
        QtCore.QObject.__init__(self, parent)
        self.map_visible = True
        self.grid_visible = True
        self.grayline_visible = True
        self.highlighted_locators = []
        self.locator_heatmap = _grid.LocatorHeatmap()

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

    def highlight_locator(self, locator):
        self.highlighted_locators.append(locator)
        self.changed.emit()

    def highlight_locators(self, locators):
        self.highlighted_locators = locators
        self.changed.emit()

    def clear_locator(self, locator):
        self.highlighted_locators.remove(locator)
        self.changed.emit()

    def clear_all_locators(self):
        self.highlighted_locators = []
        self.changed.emit()

    def add_heat(self, locator, heat = 10):
        self.locator_heatmap.add(locator, heat)
        self.changed.emit()

    def set_heat(self, locator_heatmap):
        self.locator_heatmap = locator_heatmap
        self.changed.emit()

    def clear_heatmap(self):
        self.locator_heatmap = _grid.LocatorHeatmap()
        self.changed.emit()


class MapWidget(QtGui.QWidget):
    def __init__(self, map, parent = None):
        QtGui.QWidget.__init__(self, parent)
        self.map = map
        self.map.changed.connect(self.repaint)
        self.world_graphic = QtSvg.QGraphicsSvgItem(os.path.join(os.path.dirname(os.path.abspath(__file__)), "map.svg"))

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        self.draw_widget(painter)
        painter.end()

    def sizeHint(self):
        return self._size_in_ratio()

    def _size_in_ratio(self):
        size = self.size()
        height_for_width = int(size.width() / 2)
        width_for_height = size.height() * 2
        if height_for_width <= size.height(): return QtCore.QSize(size.width(), height_for_width)
        else: return QtCore.QSize(width_for_height, size.height())

    def draw_widget(self, painter):
        size = self._size_in_ratio()
        box = QtCore.QRect((self.size().width() - size.width()) / 2, (self.size().height() - size.height()) / 2, size.width(), size.height())

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
        self._draw_highlighted_locators(painter)
        self._draw_locator_heatmap(painter)

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

    def _draw_highlighted_locators(self, painter):
        for locator in self.map.highlighted_locators:
            self._draw_locator(painter, locator)

    def _draw_locator_heatmap(self, painter):
        for latlon in self.map.locator_heatmap.heatmap:
            heat = float(self.map.locator_heatmap.heatmap[latlon]) / float(self.map.locator_heatmap.max_heat)
            self._draw_lat_lon(painter, latlon, color = self._heat_color(heat), opacity = 0.5 * heat + 0.5)

    def _draw_locator(self, painter, locator, color = QtGui.QColor(255, 0, 0), opacity = 1):
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

    def _draw_lat_lon(self, painter, latlon, width = 2, height = 1, color = QtGui.QColor(255, 0, 0), opacity = 1):
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
    def __init__(self, dxcc, bandmap, map, parent = None):
        _windowmanager.ManagedWindow.__init__(self, parent)
        self.setObjectName("map")
        self.setWindowTitle("Map")
        self.resize(1200, 600)
        self.dxcc = dxcc
        self.bandmap = bandmap
        self.map = map

        self.map_widget = MapWidget(map)

        show_map = QtGui.QCheckBox()
        show_map.setText("Karte")
        show_map.setCheckState(QtCore.Qt.Checked if self.map.map_visible else QtCore.Qt.Unchecked)
        show_map.stateChanged.connect(self.map.show_map)

        show_grid = QtGui.QCheckBox()
        show_grid.setText("Locator-Gitter")
        show_grid.setCheckState(QtCore.Qt.Checked if self.map.grid_visible else QtCore.Qt.Unchecked)
        show_grid.stateChanged.connect(self.map.show_grid)

        show_grayline = QtGui.QCheckBox()
        show_grayline.setText("Tag/Nacht-Grenze")
        show_grayline.setCheckState(QtCore.Qt.Checked if self.map.grayline_visible else QtCore.Qt.Unchecked)
        show_grayline.stateChanged.connect(self.map.show_grayline)

        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(show_map)
        hbox.addWidget(show_grid)
        hbox.addWidget(show_grayline)

        vbox = QtGui.QVBoxLayout()
        vbox.addLayout(hbox)
        vbox.addWidget(self.map_widget)

        self.setLayout(vbox)

        self.bandmap.update_spots.connect(self._highlight_spots)

    def _highlight_spots(self, spots):
        heatmap = _grid.LocatorHeatmap()
        for spot in spots:
            info = self.dxcc.find_dxcc_info(spot.call)
            if not info: continue
            locator = _grid.Locator.from_lat_lon(info.latlon)
            heatmap.add(locator, 1)
        self.map.set_heat(heatmap)


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
    bandmap = _bandmap.BandMap(dxcc)
    map = Map()

    win = MapWindow(dxcc, bandmap, map)
    win.show()

    clusters = [] #config.clusters
    spotting_file = "../rbn.txt"

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

if __name__ == "__main__": main(sys.argv)
