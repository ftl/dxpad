#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Manage the storage and retrieval of window geometry and visibility. 

There is a big hack ongoing for X11, since QWidget.restoreGeometry does
not work as expected here. We are restoring the window geometry on the
first paint event. This is the first point in time when the window
manager has finally created all required decoration and the window will
actually end on the stored position. Otherwise it would be shifted by 
some offset, depending on the window manager implementation.

There is also temporal coupling between window.resize and window.move.
If you move first and then resize, the window will end up at a different
position in some cases. This is because move makes sure that your
window is completely on the screen.

What a mess...
"""

import sys
import os
import base64

from PySide import QtCore, QtGui

from . import _config

class WindowManager:
    def __init__(self, parent = None):
        self.settings = QtCore.QSettings(
            _config.filename("windows.ini"), QtCore.QSettings.IniFormat)
        self.windows = {}

    def restore_window_geometry(self, window):
        name = str(window.objectName())
        window.resize(self.settings.value(name + "/size", window.size()))
        window.move(self.settings.value(name + "/pos", window.pos()))

    def save_window_geometry(self, window):
        name = str(window.objectName())
        self.settings.setValue(name + "/size", window.size())
        self.settings.setValue(name + "/pos", window.pos())
        self.settings.sync()

    def restore_visibility(self):
        pass

    def save_visibility(self):
        pass

    def add_window(self, window):
        self.windows[window.objectName()] = window
        if hasattr(window, "restore_geometry"):
            window.restore_geometry = self.restore_window_geometry
        if hasattr(window, "save_geometry"):
            window.save_geometry = self.save_window_geometry
        if hasattr(window, "save_visibility"):
            window.save_visibility = self.save_visibility

class ManagedMainWindow(QtGui.QMainWindow):
    def __init__(self, parent = None):
        QtGui.QMainWindow.__init__(self, parent)
        self.geometry_restored = False
        self.restore_geometry = None
        self.save_geometry = None
        self.save_visibility = None

    def paintEvent(self, e):
        QtGui.QMainWindow.paintEvent(self, e)
        if self.restore_geometry and not self.geometry_restored:
            self.restore_geometry(self)
            self.geometry_restored = True

    def closeEvent(self, e):
        if self.save_geometry:
            self.save_geometry(self)
        if self.save_visibility:
            self.save_visibility()
        QtGui.QMainWindow.closeEvent(self, e)

class ManagedWindow(QtGui.QWidget):
    def __init__(self, parent = None):
        QtGui.QWidget.__init__(self, parent)
        self.geometry_restored = False
        self.restore_geometry = None
        self.save_geometry = None

    def paintEvent(self, e):
        QtGui.QMainWindow.paintEvent(self, e)
        if self.restore_geometry and not self.geometry_restored:
            self.restore_geometry(self)
            self.geometry_restored = True

    def closeEvent(self, e):
        if self.save_geometry:
            self.save_geometry(self)
        QtGui.QWidget.closeEvent(self, e)

class MasterWindow(ManagedMainWindow):
    def __init__(self, app, window_manager, slave_window, parent = None):
        ManagedMainWindow.__init__(self, parent)
        self.setObjectName("master_window")
        self.setWindowTitle("Master Window")
        self.app = app
        self.window_manager = window_manager
        self.slave_window = slave_window

        show_button = QtGui.QPushButton("Show Slave")
        show_button.clicked.connect(self.show_slave)

        restore_button = QtGui.QPushButton("Restore Slave")
        restore_button.clicked.connect(self.restore_slave)

        save_button = QtGui.QPushButton("Save Slave")
        save_button.clicked.connect(self.save_slave)

        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(show_button)
        vbox.addWidget(restore_button)
        vbox.addWidget(save_button)
        vbox.addStretch()

        frame = QtGui.QFrame()
        frame.setLayout(vbox)
        self.setCentralWidget(frame)

    def show_slave(self):
        self.slave_window.show()
        self.app.setActiveWindow(self.slave_window)

    def restore_slave(self):
        self.slave_window.show()
        self.window_manager.restore_window_geometry(self.slave_window)

    def save_slave(self):
        self.window_manager.save_window_geometry(self.slave_window)

    def closeEvent(self, e):
        ManagedMainWindow.closeEvent(self, e)
        self.app.quit()

class SlaveWindow(ManagedWindow):
    def __init__(self, parent = None):
        ManagedWindow.__init__(self, parent)
        self.setObjectName("slave_window")
        self.setWindowTitle("Slave Window")

def main(args):
    window_manager = WindowManager()
    
    app = QtGui.QApplication(args)
    app.aboutToQuit.connect(app.closeAllWindows)

    slave = SlaveWindow()
    master = MasterWindow(app, window_manager, slave)

    window_manager.add_window(master)
    window_manager.add_window(slave)
    window_manager.restore_visibility()

    master.show()
    master.setFocus()

    result = app.exec_()

    sys.exit(result)
