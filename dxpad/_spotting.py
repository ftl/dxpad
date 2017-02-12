#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, time, re
import telnetlib as tn
from PySide import QtCore, QtGui

class Spot:
	def __init__(self, call, frequency, time, source_call, source_grid):
		self.call = call
		self.frequency = frequency
		self.time = time
		self.source_call = source_call
		self.source_grid = source_grid

	def __str__(self):
		return "source(" + self.source_call + ", " + self.source_grid + ") spot(" + self.call + ", " + str(self.frequency) + ", " + str(self.time) + ")" 

class ClusterSpot(Spot):
	def __init__(self, call, frequency, time, source_call, source_grid, comment):
		Spot.__init__(self, call, frequency, time, source_call, source_grid)
		self.comment = comment

	def __str__(self):
		return Spot.__str__(self) + " cluster(" + self.comment + ")"


class RbnSpot(Spot):
	def __init__(self, call, frequency, time, source_call, source_grid, mode, rssi, speed, rbnType):
		Spot.__init__(self, call, frequency, time, source_call, source_grid)
		self.mode = mode
		self.rssi = rssi
		self.speed = speed
		self.rbnType = rbnType

	def __str__(self):
		return Spot.__str__(self) + " rbn(" + self.mode + ", " + self.rssi + ", " + self.speed + ", " + self.rbnType + ")"

class TelnetClient:
	def __init__(self, hostname, port, call, password = ""):
		self.hostname = hostname
		self.port = port
		self.call = call
		self.password = password
		self.running = False

	def run(self, line_callback):
		telnet = tn.Telnet(self.hostname, self.port)
		print("Connected to {}:{}".format(self.hostname, self.port))
		self.running = True

		buffer = ""
		while self.running:
			buffer += telnet.read_some()
			while buffer.find("\n") != -1:
				line, buffer = buffer.split("\n", 1)
				line_callback(line)
			if buffer.endswith("Please enter your call: "):
				telnet.write(self.call + "\n")
			if buffer.endswith("callsign: "):
				telnet.write(self.call + "\n")
			if buffer.endswith("login: "):
				telnet.write(self.call + "\n")
			if buffer.endswith("password: "):
				telnet.write(self.password + "\n")

		telnet.close()

	def stop(self):
		self.running = False

class TextfileClient:
	def __init__(self, filename):
		self.filename = filename
		self.running = False

	def run(self, line_callback):
		self.running = True
		while self.running:
			with open(self.filename) as f:
				for line in f:
					line_callback(line)
					time.sleep(0.1) # ???
					if not self.running: break

	def stop(self):
		self.running = False

class ClusterSpotter:
	_spot_expression = re.compile(r'DX de ([A-Z0-9/]+)(-.+?)?:?\s*([0-9]+\.[0-9]+)\s+([A-Z0-9/]+)\s+(.+?)\s([0-9]{4})Z(\s+([A-Z]{2}[0-9]{2}))?')
	_rbn_comment_expression = re.compile(r'([A-Z0-9]+)\s+([0-9]+) dB\s+([0-9]+) (WPM|BPS)\s+(.*)\s*')

	def __init__(self, client):
		self.client = client

	def run(self, spot_callback):
		self.client.run(lambda line: self._line_received(line, spot_callback))

	def stop(self):
		self.client.stop()

	def is_running(self):
		return self.client.running

	def _line_received(self, line, spot_callback):
		spot_match = self._spot_expression.match(line)
		if not spot_match:
			print line
			return
		
		call = spot_match.group(4)
		frequency = float(spot_match.group(3))
		timestamp = time.time()
		source_call = spot_match.group(1)
		source_grid = str(spot_match.group(8))
		comment = spot_match.group(5).strip()

		rbn_comment_match = self._rbn_comment_expression.match(comment)
		if rbn_comment_match:
			mode = rbn_comment_match.group(1)
			rssi = rbn_comment_match.group(2)
			speed = rbn_comment_match.group(3)
			rbnType = rbn_comment_match.group(5)
			spot = RbnSpot(call, frequency, timestamp, source_call, source_grid, mode, rssi, speed, rbnType)
		else:
			spot = ClusterSpot(call, frequency, timestamp, source_call, source_grid, comment)
		spot_callback(spot)

class SpottingThread(QtCore.QThread):
	spot_received = QtCore.Signal(object)

	def __init__(self, client, parent = None):
		QtCore.QThread.__init__(self, parent)
		self.spotter = ClusterSpotter(client)

	@staticmethod
	def telnet(hostname, port, call, password = ""):
		client = TelnetClient(hostname, port, call, password)
		return SpottingThread(client)

	@staticmethod
	def textfile(filename):
		client = TextfileClient(filename)
		return SpottingThread(client)

	def run(self):
		self.spotter.run(lambda spot: self.spot_received.emit(spot))

	@QtCore.Slot()
	def stop(self):
		self.spotter.stop()

@QtCore.Slot(object)
def spot_received(spot):
	print str(spot)

if __name__ == "__main__":
	app = QtGui.QApplication(sys.argv)

	wid = QtGui.QWidget()
	wid.resize(250, 150)
	wid.setWindowTitle('Simple')
	wid.show()

	st = SpottingThread.textfile("rbn.txt")
	st.spot_received.connect(spot_received)
	st.start()

	result = app.exec_()
	
	st.stop()
	st.wait()

	sys.exit(result)

# arcluster.reversebeacon.net: (RBN)
# DX de EA5WU-#:   14049.6  G4LEM          CW    14 dB  18 WPM  CQ      0916Z
# DX de ON5KQ-1-#:   7019.0  IZ5CPK         CW    20 dB  26 WPM  CQ      0915Z
# DX de DL9GTB-#:  14071.0  UR4EYN         PSK31 44 dB  31 BPS  CQ      1026Z

# dxc.db0hst.de: (DX Spider)
# DX de JE7ETY:     3525.0  E51DWC       cq up                          0917Z
# DX de W3LPL:      3525.1  E51DWC       Heard in WA                    0919Z FM19

# db0ovp.de: (DX Spider)
# DX de BG8NUD:     7014.2  CX2AQ        QSX 7015.20 CW                 0923Z OL36
# DX de PA5XMM:    18082.0  A61Q                                        0922Z
# DX de EI55WAW     7046.5  EI55WAW      ses rtty                       1604Z

# cluster.dl9gtb.de:8000 (AR-Cluster):
# DX de ON7WN:      7093.0  OT6V/P       onff 0230 : Rene               1001Z

# cluster.dl9gtb.de:7373 (CC Cluster):
# DX de HL2WA:      7026.0  9M2PUL       tnx QSO                        1002Z
