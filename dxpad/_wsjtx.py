#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, socket, struct
from PySide import QtCore, QtGui

import _config

class IncomingMessage:
	def __init__(self, data):
		self.data = data
		self.current_index = 0
		self.last_index = len(data)
		self.magic_number = self.read_quint32()
		self.schema_number = self.read_quint32()
		self.id = self.read_quint32()

	def __str__(self):
		return ":".join("{:02x}".format(ord(c)) for c in self.data)

	def reset(self):
		self.current_index = 12

	def read_bool(self):
		if self.current_index >= self.last_index: return False
		start = self.current_index
		self.current_index += 1
		return struct.unpack(">?", self.data[start:(self.current_index)])[0]

	def read_quint8(self):
		if self.current_index >= self.last_index: return 0
		start = self.current_index
		self.current_index += 1
		return struct.unpack(">B", self.data[start:(self.current_index)])[0]

	def read_quint32(self):
		if self.current_index >= self.last_index: return 0
		start = self.current_index
		self.current_index += 4
		return struct.unpack(">L", self.data[start:(self.current_index)])[0]

	def read_qint32(self):
		if self.current_index >= self.last_index: return 0
		start = self.current_index
		self.current_index += 4
		return struct.unpack(">l", self.data[start:(self.current_index)])[0]

	def read_quint64(self):
		if self.current_index >= self.last_index: return 0
		start = self.current_index
		self.current_index += 8
		return struct.unpack(">Q", self.data[start:(self.current_index)])[0]

	def read_time(self):
		return self.read_quint32() # milliseconds since midnight

	def read_datetime(self):
		if self.current_index >= self.last_index: return 0
		julian_day = self.read_quint64()
		ms_since_midnight = self.read_time()
		timespec = self.read_quint8()
		if timespec == 2:
			offset = self.read_quint32()
		else:
			offset = 0
		seconds_since_epoc = int((julian_day - 2440587.5) * 86400.0 + (ms_since_midnight / 1000.0))
		return seconds_since_epoc

	def read_float(self):
		if self.current_index >= self.last_index: return 0.0
		start = self.current_index
		self.current_index += 8
		return struct.unpack(">d", self.data[start:(self.current_index)])[0]

	def read_utf8(self):
		if self.current_index >= self.last_index: return None
		length = self.read_quint32()
		if length == 0xFFFFFFFF: return None
		start = self.current_index
		self.current_index += length
		return unicode(self.data[start:(self.current_index)])


class WsjtxParser(QtCore.QObject):
	heartbeat = QtCore.Signal(str, int, str, str)
	status = QtCore.Signal(str, int, str, str, str, str, bool, bool, bool, int, int, str, str, str, bool, str, bool)
	decode = QtCore.Signal(str, bool, int, int, float, int, str, str)
	clear = QtCore.Signal(str)
	log_qso = QtCore.Signal(str, int, str, str, int, str, str, str, str, str, str, int)
	close = QtCore.Signal(str)
	wspr_decode = QtCore.Signal(str, bool, int, int, float, int, int, str, str, int)

	def __init__(self, parent = None):
		QtCore.QObject.__init__(self, parent)
		self.MSG_HANDLERS = {
			0: self._read_heartbeat,
			1: self._read_status,
			2: self._read_decode,
			3: self._read_clear,
			5: self._read_log_qso,
			6: self._read_close,
			10: self._read_wspr_decode
		}

	@QtCore.Slot(object, object)
	def parse_message(self, data, address):
		print "incoming message from " + str(address)
		message = IncomingMessage(data)
		# print str(message)

		if message.id in self.MSG_HANDLERS:
			self.MSG_HANDLERS[message.id](message)
		else:
			self._handle_unknown_message(message)

	def _read_heartbeat(self, message):
		unique_id = message.read_utf8()
		maximum_schema_number = message.read_quint32()
		version = message.read_utf8()
		revision = message.read_utf8()
		self.heartbeat.emit(unique_id, maximum_schema_number, version, revision)

	def _read_status(self, message):
		unique_id = message.read_utf8()
		frequency_Hz = message.read_quint64()
		mode = message.read_utf8()
		dx_call = message.read_utf8()
		report = message.read_utf8()
		tx_mode = message.read_utf8()
		tx_enabled = message.read_bool()
		transmitting = message.read_bool()
		decoding = message.read_bool()
		rx_df = message.read_quint32()
		tx_df = message.read_quint32()
		de_call = message.read_utf8()
		de_grid = message.read_utf8()
		dx_grid = message.read_utf8()
		tx_watchdog = message.read_bool()
		sub_mode = message.read_utf8()
		fast_mode = message.read_bool()
		self.status.emit(unique_id, frequency_Hz, mode, dx_call, report, tx_mode, tx_enabled, transmitting, decoding, rx_df, tx_df, de_call, de_grid, dx_grid, tx_watchdog, sub_mode, fast_mode)

	def _read_decode(self, message):
		unique_id = message.read_utf8()
		new = message.read_bool()
		ms_since_midnight = message.read_time()
		snr = message.read_qint32()
		delta_time_seconds = message.read_float()
		delta_freqzency_Hz = message.read_quint32()
		mode = message.read_utf8()
		message_content = message.read_utf8()
		self.decode.emit(unique_id, new, ms_since_midnight, snr, delta_time_seconds, delta_freqzency_Hz, mode, message_content)

	def _read_clear(self, message):
		unique_id = message.read_utf8()
		self.clear.emit(unique_id)

	def _read_log_qso(self, message):
		unique_id = message.read_utf8()
		timestamp_begin = message.read_datetime()
		dx_call = message.read_utf8()
		dx_grid = message.read_utf8()
		frequency_Hz = message.read_quint64()
		mode = message.read_utf8()
		report_send = message.read_utf8()
		report_received = message.read_utf8()
		tx_power = message.read_utf8()
		comments = message.read_utf8()
		name = message.read_utf8()
		timestamp_end = message.read_datetime()
		self.log_qso.emit(unique_id, timestamp_begin, dx_call, dx_grid, frequency_Hz, mode, report_send, report_received, tx_power, comments, name, timestamp_end)

	def _read_close(self, message):
		unique_id = message.read_utf8()
		self.close.emit(unique_id)

	def _read_wspr_decode(self, message):
		unique_id = message.read_utf8()
		new = message.read_bool()
		ms_since_midnight = message.read_time()
		snr = message.read_quint32()
		delta_time_seconds = message.read_float()
		frequency_Hz = message.read_quint64()
		drift_Hz = message.read_quint32()
		callsign = message.read_utf8()
		grid = message.read_utf8()
		power_dBm = message.read_quint32()
		self.wspr_decode.emit(unique_id, new, ms_since_midnight, snr, delta_time_seconds, frequency_Hz, drift_Hz, callsign, grid, power_dBm)

	def _handle_unknown_message(self, message):
		print "unknown message " + str(message.id)

class WsjtxReceiver(QtCore.QThread):
	message_received = QtCore.Signal(object, object)

	def __init__(self, host = "127.0.0.1", port = 2237, parent = None):
		QtCore.QThread.__init__(self, parent)
		self.host = host
		self.port = port
		self.running = False

	def run(self):
		self.running = True
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		sock.bind((self.host, self.port))
		sock.settimeout(1.0)
		while self.running:
			try:
				data, address = sock.recvfrom(1024)
				self.message_received.emit(data, address)
			except:
				pass

	@QtCore.Slot()
	def stop(self):
		self.running = False

class WsjtxRepeater(QtCore.QObject):
	def __init__(self, host = "127.0.0.1", port = 22370, parent = None):
		QtCore.QObject.__init__(self, parent)
		self.host = host
		self.port = port
		self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

	@QtCore.Slot(object, object)
	def send_message(self, data, address):
		self.socket.sendto(data, (self.host, self.port))


def print_heartbeat(unique_id, maximum_schema_number, version, revision):
	print "heartbeat"
	print "\tunique id " + unique_id
	print "\tmaximum_schema_number " + str(maximum_schema_number)
	print "\tversion " + version
	print "\trevision " + revision

def print_status(unique_id, frequency_Hz, mode, dx_call, report, tx_mode, tx_enabled, transmitting, decoding, rx_df, tx_df, de_call, de_grid, dx_grid, tx_watchdog, sub_mode, fast_mode):
	print "status"
	print "\tunique id " + unique_id
	print "\tfrequency " + str(frequency_Hz)
	print "\tdx call " + str(dx_call)

def print_decode(unique_id, new, ms_since_midnight, snr, delta_time_seconds, delta_freqzency_Hz, mode, message_content):
	print "decode"
	print "\tmessage " + str(message_content)

def print_clear(unique_id):
	print "clear"

def print_log_qso(unique_id, timestamp_begin, dx_call, dx_grid, frequency_Hz, mode, report_send, report_received, tx_power, comments, name, timestamp_end):
	print "log qso"

def print_close(unique_id):
	print "close"

def print_wspr_decode(unique_id, new, ms_since_midnight, snr, delta_time_seconds, frequency_Hz, drift_Hz, callsign, grid, power_dBm):
	print "wspr_decode"

def main(args):
	app = QtGui.QApplication(args)

	config = _config.load_config().get_wsjtx()

	wid = QtGui.QWidget()
	wid.resize(250, 150)
	wid.setWindowTitle('Simple')
	wid.show()

	parser = WsjtxParser()
	receiver = WsjtxReceiver(host = config.listen_host, port = config.listen_port)
	repeater = WsjtxRepeater(host = config.repeater_host, port = config.repeater_port)

	receiver.message_received.connect(parser.parse_message)
	if config.repeater:
		print "Repeater active"
		receiver.message_received.connect(repeater.send_message)

	parser.heartbeat.connect(print_heartbeat)
	parser.status.connect(print_status)
	parser.decode.connect(print_decode)
	parser.clear.connect(print_clear)
	parser.log_qso.connect(print_log_qso)
	parser.close.connect(print_close)
	parser.wspr_decode.connect(print_wspr_decode)

	receiver.start()

	result = app.exec_()

	receiver.stop()
	receiver.wait()

	sys.exit(result)

if __name__ == "__main__": main(sys.argv)
