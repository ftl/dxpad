#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

from PySide import QtGui

from . import _bandmap, _dxcc, _map, _spotting, _pskreporter, _infohub, \
              _hamqth, _qrz, _notepad, _entry, _config, _windowmanager, _wsjtx

class MainWindow(_windowmanager.ManagedMainWindow):
    def __init__(self, app, entry_line, notepad, parent = None):
        _windowmanager.ManagedMainWindow.__init__(self, parent)
        self.setObjectName("main")
        self.app = app
        self.entry_line = entry_line
        self.notepad = notepad

        self.line_widget = _entry.EntryWidget(entry_line)
        self.notepad_widget = _notepad.NotepadWidget(notepad)

        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.notepad_widget)
        vbox.addWidget(self.line_widget)
        frame = QtGui.QFrame()
        frame.setLayout(vbox)

        self.setCentralWidget(frame)
        self.setFocusProxy(self.line_widget)
        self.setWindowTitle("DXPad")
        self.resize(800, 400)

    def closeEvent(self, e):
        _windowmanager.ManagedMainWindow.closeEvent(self, e)
        self.app.quit()

def main(args):
    app = QtGui.QApplication(sys.argv)
    app.aboutToQuit.connect(app.closeAllWindows)

    config = _config.load_config()
    window_manager = _windowmanager.WindowManager()

    dxcc = _dxcc.DXCC()
    dxcc.load()
    aggregator = _spotting.SpotAggregator(dxcc)
    pskreporter = _pskreporter.PskReporter(config.locator)
    bandmap = _bandmap.BandMap()
    map = _map.Map()
    map.set_own_locator(config.locator)
    map.select_call(config.call)
    map.select_continents([dxcc.find_dxcc_info(config.call).continent])
    notepad = _notepad.Notepad()
    entry_line = _entry.EntryLine(notepad)
    callbooks = []
    if config.hamqth:
        callbooks.append(
            _hamqth.AsyncHamQTH(config.hamqth.user, config.hamqth.password))
    if config.qrz:
        callbooks.append(_qrz.AsyncQrz(config.qrz.user, config.qrz.password))
    infohub = _infohub.Infohub(dxcc, callbooks, config.call, config.locator)
    wsjtx_config = config.get_wsjtx()
    wsjtx = _wsjtx.WSJTX(
        wsjtx_config.listen_host, wsjtx_config.listen_port, 
        wsjtx_config.repeater, wsjtx_config.repeater_host, 
        wsjtx_config.repeater_port)


    infohub.locator_looked_up.connect(map.set_destination_locator)
    aggregator.update_spots.connect(bandmap.spots_received)
    aggregator.update_spots.connect(map.highlight_spots)
    pskreporter.spot_received.connect(aggregator.spot_received)
    notepad.call_added.connect(infohub.lookup_call)
    wsjtx.status.dx_call_updated.connect(infohub.lookup_call)

    main_window = MainWindow(app, entry_line, notepad)
    infohub_window = _infohub.InfohubWindow(infohub)
    bandmap_window = _bandmap.BandmapWindow(bandmap)
    map_window = _map.MapWindow(map)

    window_manager.add_window(main_window)
    window_manager.add_window(infohub_window)
    window_manager.add_window(bandmap_window)
    window_manager.add_window(map_window)
    window_manager.restore_visibility()

    bandmap_window.show()
    map_window.show()
    infohub_window.show()
    main_window.show()

    main_window.setFocus()

    clusters = config.clusters
    spotting_file = None #"../rbn.txt"
    aggregator.start_spotting(clusters, spotting_file)
    pskreporter.start()
    wsjtx.start()

    result = app.exec_()
    
    aggregator.stop_spotting()
    pskreporter.stop()
    wsjtx.stop()

    sys.exit(result)
