#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
from PySide import QtGui

import _bandmap, _dxcc, _map, _spotting, _infohub, _hamqth, _qrz, _notepad, _entry, _config, _windowmanager

class MainWindow(_windowmanager.ManagedMainWindow):
	def __init__(self, app, entry_line, notepad, infohub, parent = None):
		_windowmanager.ManagedMainWindow.__init__(self, parent)
		self.setObjectName("main")
		self.app = app
		self.entry_line = entry_line
		self.notepad = notepad
		self.infohub = infohub

		self.line_widget = _entry.EntryWidget(entry_line)
		self.notepad_widget = _notepad.NotepadWidget(notepad)
		self.infohub_widget = _infohub.InfohubWidget(infohub)

		vbox = QtGui.QVBoxLayout()
		vbox.addWidget(self.notepad_widget)
		vbox.addWidget(self.line_widget)
		frame = QtGui.QFrame()
		frame.setLayout(vbox)

		splitter = QtGui.QSplitter(self)
		splitter.addWidget(self.infohub_widget)
		splitter.addWidget(frame)

		main_layout = QtGui.QHBoxLayout()
		main_layout.addWidget(splitter)
		main_layout.setContentsMargins(0, 0, 0, 0)
		main_layout.setSpacing(0)
		self.setCentralWidget(splitter)
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
	dxcc.load_from_file("cty.dat")
	bandmap = _bandmap.BandMap(dxcc)
	notepad = _notepad.Notepad()
	entry_line = _entry.EntryLine(notepad)
	callbooks = []
	if config.hamqth:
		callbooks.append(_hamqth.AsyncHamQTH(config.hamqth.user, config.hamqth.password))
	if config.qrz:
		callbooks.append(_qrz.AsyncQrz(config.qrz.user, config.qrz.password))
	infohub = _infohub.Infohub(dxcc, callbooks, config.call, config.locator)
	notepad.call_added.connect(infohub.lookup_call)

	main_window = MainWindow(app, entry_line, notepad, infohub)
	bandmap_window = _bandmap.BandmapWindow(bandmap)
	map_window = _map.MapWindow(dxcc, bandmap)

	window_manager.add_window(main_window)
	window_manager.add_window(bandmap_window)
	window_manager.add_window(map_window)
	window_manager.restore_visibility()

	bandmap_window.show()
	map_window.show()
	main_window.show()

	main_window.setFocus()

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

if __name__ == "__main__": main(sys.argv)
