#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

from PySide import QtCore, QtGui

from . import _bandplan, _windowmanager


class VFO(QtCore.QObject):
    band_changed = QtCore.Signal(object)

    def __init__(self, bandplan, parent = None):
        QtCore.QObject.__init__(self, parent)
        self.bandplan = bandplan
        self.band = bandplan[5]

    def select_band(self, band):
        self.band = band
        self.band_changed.emit(self.band)


class BandswitchWidget(QtGui.QWidget):
    def __init__(self, vfo, parent = None):
        QtGui.QWidget.__init__(self, parent)
        self.vfo = vfo
        self.vfo.band_changed.connect(self._band_changed)

        self.band_buttons = QtGui.QButtonGroup()
        self.band_buttons.buttonClicked.connect(self._select_band)

        bandLayout = QtGui.QVBoxLayout()
        bandId = 0
        for band in self.vfo.bandplan:
            button = QtGui.QPushButton(band.name)
            button.setCheckable(True)
            self.band_buttons.addButton(button, bandId)
            bandLayout.addWidget(button)

            if self.vfo.band == band:
                button.setChecked(True)
            bandId += 1
        bandLayout.addStretch(1)
        bandLayout.setContentsMargins(3, 3, 3, 3)
        bandLayout.setSpacing(1)

        bandGroup = QtGui.QGroupBox("Band")
        bandGroup.setLayout(bandLayout)

        rootLayout = QtGui.QHBoxLayout()
        rootLayout.addWidget(bandGroup)
        rootLayout.setContentsMargins(0, 0, 0, 0)
        rootLayout.setSpacing(0)
        self.setLayout(rootLayout)

    def _select_band(self, button):
        band_id = self.band_buttons.checkedId()
        band = self.vfo.bandplan[band_id]
        self.vfo.select_band(band)

    def _band_changed(self, band):
        band_id = self._band_id(band)
        self.band_buttons.button(band_id).setChecked(True)

    def _band_id(self, band):
        id = 0
        for b in self.vfo.bandplan:
            if b == band: 
                return id
            id += 1
        return -1


class VFOWindow(_windowmanager.ManagedWindow):
    def __init__(self, vfo, parent = None):
        _windowmanager.ManagedWindow.__init__(self, parent)
        self.setObjectName("vfo")
        self.vfo = vfo

        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(BandswitchWidget(self.vfo))
        self.setLayout(vbox)
        self.setWindowTitle("VFO")


def main(args):
    app = QtGui.QApplication(args)

    vfo = VFO(_bandplan.IARU_REGION_1)

    vfo_win = VFOWindow(vfo)
    vfo_win.resize(300, 400)
    vfo_win.show()

    result = app.exec_()

    sys.exit(result)
