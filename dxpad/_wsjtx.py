#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import socket
import struct

from PySide import QtCore, QtGui

from . import _config, _callinfo, _grid

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
        seconds_since_epoc = int(
            (julian_day - 2440587.5) * 86400.0 + (ms_since_midnight / 1000.0))
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
        return self.data[start:(self.current_index)].decode("utf-8")


class DecodedMessage:
    def __init__(self, unique_id, new, ms_since_midnight, snr, 
            delta_time_seconds, delta_freqzency_Hz, mode, message_content):
        self.unique_id = unique_id
        self.new = new
        self.ms_since_midnight = ms_since_midnight
        self.snr = snr
        self.delta_time_seconds = delta_time_seconds
        self.delta_freqzency_Hz = delta_freqzency_Hz
        self.mode = mode
        self.message_content = message_content
        self.message_fields = message_content.split(" ") if message_content else None
        self.details = None

    def __repr__(self):
        return "Message(\"{}\")".format(str(self))

    def __str__(self):
        return "{2} {1} {0}".format(self.message_content, self.snr, 
            self.delta_freqzency_Hz)

    def is_cq(self):
        return len(self.message_fields) > 0  and (
            self.message_fields[0] == "CQ" or self.message_fields[0] == "QRZ")


class Parser(QtCore.QObject):
    heartbeat = QtCore.Signal(str, int, str, str)
    status = QtCore.Signal(
        str, int, str, str, str, str, bool, bool, bool, int, int, str, str, 
        str, bool, str, bool)
    decode = QtCore.Signal(object)
    clear = QtCore.Signal(str)
    log_qso = QtCore.Signal(
        str, int, str, str, int, str, str, str, str, str, str, int)
    close = QtCore.Signal(str)
    wspr_decode = QtCore.Signal(
        str, bool, int, int, float, int, int, str, str, int)

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
        message = IncomingMessage(data)
        if message.id in self.MSG_HANDLERS:
            self.MSG_HANDLERS[message.id](message)
        else:
            self._handle_unknown_message(message)

    def _read_heartbeat(self, message):
        unique_id = message.read_utf8()
        maximum_schema_number = message.read_quint32()
        version = message.read_utf8()
        revision = message.read_utf8()
        self.heartbeat.emit(
            unique_id, maximum_schema_number, version, revision)

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
        self.status.emit(
            unique_id, frequency_Hz, mode, dx_call, report, tx_mode, 
            tx_enabled, transmitting, decoding, rx_df, tx_df, de_call, 
            de_grid, dx_grid, tx_watchdog, sub_mode, fast_mode)

    def _read_decode(self, message):
        unique_id = message.read_utf8()
        new = message.read_bool()
        ms_since_midnight = message.read_time()
        snr = message.read_qint32()
        delta_time_seconds = message.read_float()
        delta_freqzency_Hz = message.read_quint32()
        mode = message.read_utf8()
        message_content = message.read_utf8()
        decoded_message = DecodedMessage(unique_id, new, ms_since_midnight, 
            snr, delta_time_seconds, delta_freqzency_Hz, mode, message_content)

        self.decode.emit(decoded_message)

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
        self.log_qso.emit(
            unique_id, timestamp_begin, dx_call, dx_grid, frequency_Hz, mode, 
            report_send, report_received, tx_power, comments, name, 
            timestamp_end)

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
        self.wspr_decode.emit(
            unique_id, new, ms_since_midnight, snr, delta_time_seconds, 
            frequency_Hz, drift_Hz, callsign, grid, power_dBm)

    def _handle_unknown_message(self, message):
        print("unknown message " + str(message.id))

class Receiver(QtCore.QThread):
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

class Repeater(QtCore.QObject):
    def __init__(self, host = "127.0.0.1", port = 22370, parent = None):
        QtCore.QObject.__init__(self, parent)
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    @QtCore.Slot(object, object)
    def send_message(self, data, address):
        self.socket.sendto(data, (self.host, self.port))


class Status(QtCore.QObject):
    frequency_Hz_updated = QtCore.Signal(int)
    mode_updated = QtCore.Signal(str)
    dx_call_updated = QtCore.Signal(object)
    report_updated = QtCore.Signal(str)
    tx_mode_updated = QtCore.Signal(str)
    tx_enabled_updated = QtCore.Signal(bool)
    transmitting_updated = QtCore.Signal(bool)
    decoding_updated = QtCore.Signal(bool)
    rx_df_updated = QtCore.Signal(int)
    tx_df_updated = QtCore.Signal(int)
    de_call_updated = QtCore.Signal(object)
    de_grid_updated = QtCore.Signal(object)
    dx_grid_updated = QtCore.Signal(object)
    tx_watchdog_updated = QtCore.Signal(bool)
    sub_mode_updated = QtCore.Signal(str)
    fast_mode_updated = QtCore.Signal(bool)

    def __init__(self, parent = None):
        QtCore.QObject.__init__(self, parent)
        self.unique_id = None
        self.frequency_Hz = 0
        self.mode = None
        self.dx_call = None
        self.report = None
        self.tx_mode = None
        self.tx_enabled = False
        self.transmitting = False
        self.decoding = False
        self.rx_df = 0
        self.tx_df = 0
        self.de_call = None
        self.de_grid = None
        self.dx_grid = None
        self.tx_watchdog = False
        self.sub_mode = None
        self.fast_mode = False

    @QtCore.Slot(
        str, int, str, str, str, str, bool, bool, bool, int, int, str, str, 
        str, bool, str, bool)
    def update(
            self, unique_id, frequency_Hz, mode, dx_call, report, tx_mode, 
            tx_enabled, transmitting, decoding, rx_df, tx_df, de_call, 
            de_grid, dx_grid, tx_watchdog, sub_mode, fast_mode):
        self.unique_id = unique_id
        self._update_frequency_Hz(frequency_Hz)
        self._update_mode(mode)
        self._update_dx_call(_callinfo.Call(dx_call) if _callinfo.Call.is_valid_call(dx_call) else None)
        self._update_report(report)
        self._update_tx_mode(tx_mode)
        self._update_tx_enabled(tx_enabled)
        self._update_transmitting(transmitting)
        self._update_decoding(decoding)
        self._update_rx_df(rx_df)
        self._update_tx_df(tx_df)
        self._update_de_call(_callinfo.Call(de_call) if _callinfo.Call.is_valid_call(de_call) else None)
        self._update_de_grid(_grid.Locator(de_grid) if _grid.Locator.is_valid_locator(de_grid) else None)
        self._update_dx_grid(_grid.Locator(dx_grid) if _grid.Locator.is_valid_locator(dx_grid) else None)
        self._update_tx_watchdog(tx_watchdog)
        self._update_sub_mode(sub_mode)
        self._update_fast_mode(fast_mode)

    def _update_frequency_Hz(self, frequency_Hz):
        if self.frequency_Hz != frequency_Hz:
            self.frequency_Hz = frequency_Hz
            self.frequency_Hz_updated.emit(frequency_Hz)

    def _update_mode(self, mode):
        if self.mode != mode:
            self.mode = mode
            self.mode_updated.emit(mode)

    def _update_dx_call(self, dx_call):
        if self.dx_call != dx_call:
            self.dx_call = dx_call
            self.dx_call_updated.emit(dx_call)

    def _update_report(self, report):
        if self.report != report:
            self.report = report
            self.report_updated.emit(report)

    def _update_tx_mode(self, tx_mode):
        if self.tx_mode != tx_mode:
            self.tx_mode = tx_mode
            self.tx_mode_updated.emit(tx_mode)

    def _update_tx_enabled(self, tx_enabled):
        if self.tx_enabled != tx_enabled:
            self.tx_enabled = tx_enabled
            self.tx_enabled_updated.emit(tx_enabled)

    def _update_transmitting(self, transmitting):
        if self.transmitting != transmitting:
            self.transmitting = transmitting
            self.transmitting_updated.emit(transmitting)

    def _update_decoding(self, decoding):
        if self.decoding != decoding:
            self.decoding = decoding
            self.decoding_updated.emit(decoding)

    def _update_rx_df(self, rx_df):
        if self.rx_df != rx_df:
            self.rx_df = rx_df
            self.rx_df_updated.emit(rx_df)

    def _update_tx_df(self, tx_df):
        if self.tx_df != tx_df:
            self.tx_df = tx_df
            self.tx_df_updated.emit(tx_df)

    def _update_de_call(self, de_call):
        if self.de_call != de_call:
            self.de_call = de_call
            self.de_call_updated.emit(de_call)

    def _update_de_grid(self, de_grid):
        if self.de_grid != de_grid:
            self.de_grid = de_grid
            self.de_grid_updated.emit(de_grid)

    def _update_dx_grid(self, dx_grid):
        if self.dx_grid != dx_grid:
            self.dx_grid = dx_grid
            self.dx_grid_updated.emit(dx_grid)

    def _update_tx_watchdog(self, tx_watchdog):
        if self.tx_watchdog != tx_watchdog:
            self.tx_watchdog = tx_watchdog
            self.tx_watchdog_updated.emit(tx_watchdog)

    def _update_sub_mode(self, sub_mode):
        if self.sub_mode != sub_mode:
            self.sub_mode = sub_mode
            self.sub_mode_updated.emit(sub_mode)

    def _update_fast_mode(self, fast_mode):
        if self.fast_mode != fast_mode:
            self.fast_mode = fast_mode
            self.fast_mode_updated.emit(fast_mode)


class WSJTX(QtCore.QObject):
    def __init__(
            self, listen_host = "127.0.0.1", listen_port = 2237, 
            repeater = False, repeater_host = "127.0.0.1", 
            repeater_port = 22370, parent = None):
        QtCore.QObject.__init__(self, parent)
        self.receiver = Receiver(host = listen_host, port = listen_port)
        self.parser = Parser()
        self.status = Status()

        self.receiver.message_received.connect(self.parser.parse_message)
        self.parser.status.connect(self.status.update)
        if repeater:
            self.repeater = Repeater(
                host = repeater_host, port = repeater_port)
            self.receiver.message_received.connect(self.repeater.send_message)

    @QtCore.Slot()
    def start(self):
        self.receiver.start()

    @QtCore.Slot()
    def stop(self):
        self.receiver.stop()
        self.receiver.wait()


class CQWatch(QtCore.QObject):
    def __init__(self, parent = None):
        QtCore.QObject.__init__(self, parent)
        self.cq_calls = []

    def decoding_updated(self, decoding):
        if decoding:
            self.cq_calls = []
        else:
            print("Calling CQ:")
            print("\n".join(map(str, self.cq_calls)))

    def decode(self, message):
        if message.is_cq():
            self.cq_calls.append(message)


def print_heartbeat(unique_id, maximum_schema_number, version, revision):
    print("heartbeat")
    print("\tunique id " + unique_id)
    print("\tmaximum_schema_number " + str(maximum_schema_number))
    print("\tversion " + version)
    print("\trevision " + revision)

def print_decode(message):
    print("decode")
    print("\tmessage " + str(decoded_message))

def print_clear(unique_id):
    print("clear")

def print_log_qso(
        unique_id, timestamp_begin, dx_call, dx_grid, frequency_Hz, mode, 
        report_send, report_received, tx_power, comments, name, timestamp_end):
    print("log qso")

def print_close(unique_id):
    print("close")

def print_wspr_decode(
        unique_id, new, ms_since_midnight, snr, delta_time_seconds, 
        frequency_Hz, drift_Hz, callsign, grid, power_dBm):
    print("wspr_decode")

def print_dx_call_updated(dx_call):
    print("DX Call: " + str(dx_call))

def print_transmitting_updated(transmitting):
    print("Transmitting: " + str(transmitting))

def print_decoding_updated(decoding):
    print("Decoding: " + str(decoding))

def main(args):
    app = QtGui.QApplication(args)

    config = _config.load_config().get_wsjtx()

    wid = QtGui.QWidget()
    wid.resize(250, 150)
    wid.setWindowTitle('Simple')
    wid.show()

    wsjtx = WSJTX(
        config.listen_host, config.listen_port, config.repeater, 
        config.repeater_host, config.repeater_port)

    cq_watch = CQWatch()
    wsjtx.status.decoding_updated.connect(cq_watch.decoding_updated)
    wsjtx.parser.decode.connect(cq_watch.decode)

#    wsjtx.parser.heartbeat.connect(print_heartbeat)
#    wsjtx.parser.decode.connect(print_decode)
#    wsjtx.parser.clear.connect(print_clear)
#    wsjtx.parser.log_qso.connect(print_log_qso)
#    wsjtx.parser.close.connect(print_close)
#    wsjtx.parser.wspr_decode.connect(print_wspr_decode)

#    wsjtx.status.dx_call_updated.connect(print_dx_call_updated)
#    wsjtx.status.transmitting_updated.connect(print_transmitting_updated)
#    wsjtx.status.decoding_updated.connect(print_decoding_updated)

    wsjtx.start()

    result = app.exec_()

    wsjtx.stop()

    sys.exit(result)
