#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import socket

from PySide import QtCore, QtGui

class _Connection(QtCore.QThread):
    message_received = QtCore.Signal(str)

    def __init__(self, local_host = "127.0.0.1", local_port = 56789,
                       dest_host = "127.0.0.1", dest_port = 6789,
                       parent = None):
        QtCore.QThread.__init__(self, parent)
        self.local_address = (local_host, local_port)
        self.dest_address = (dest_host, dest_port)
        self.running = False
        self.buffer = []

    def run(self):
        self.running = True
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.bind(self.local_address)
            s.settimeout(0.5)
            self.socket = s
            while self.running:
                while len(self.buffer):
                    packet = self.buffer.pop(0)
                    s.sendto(packet.encode("utf-8"), self.dest_address)

                try:
                    data, address = s.recvfrom(1024)
                    self.message_received.emit(data.decode("utf-8"))
                except:
                    pass

    @QtCore.Slot(str)
    def send(self, data):
        self.buffer.append(data)

    def abort(self):
        self.buffer = []

    @QtCore.Slot()
    def stop(self):
        self.running = False


class CWDaemon(QtCore.QObject):
    idle = QtCore.Signal()
    busy = QtCore.Signal()

    def __init__(self, local_host = "127.0.0.1", local_port = 56789,
                       dest_host = "127.0.0.1", dest_port = 6789,
                       parent = None):
        QtCore.QObject.__init__(self, parent)
        self.connection = _Connection(local_host, local_port, dest_host, 
                                     dest_port, self)
        self.connection.message_received.connect(self._message_received)
        self.in_index = 0
        self.out_index = 0

    def start(self):
        self.connection.start()

    def stop(self):
        self.connection.stop()
        self.connection.wait()

    def _message_received(self, message):
        if message[0] == "h":
            self.out_index = int(message[1:])
            if self.out_index == self.in_index:
                self.idle.emit()
        elif message == "break\r\n":
            self.in_index = 0
            self.out_index = 0
            self.idle.emit()
        else:
            print("unknown message {}".format(message))

    def send_text(self, text):
        if self.in_index == self.out_index:
            self.busy.emit()
        self.in_index += 1
        self._send_command("h", self.in_index)
        self.connection.send(" " + text)

    def _send_command(self, command, value = ""):
        self.connection.send("\x1b{}{}".format(command, value))

    def abort(self):
        self.connection.abort()
        self._send_command(4)

    def reset(self):
        self._send_command(0)

    def set_speed(self, speed):
        self.speed = speed
        self._send_command(2, self.speed)

    def set_tone(self, tone):
        self.tone = tone
        self._send_command(3, self.tone)

    def set_sound_off(self):
        self._send_command(3, 0)

    def set_weight(self, weight):
        self.weight = weight
        self._send_command(7, weight)

    def tune(self, duration):
        self._send_command("c", duration)

    def set_ptt_delay(self, delay):
        self.ptt_delay = delay
        self._send_command("d", delay)

    def set_band_index(self, band_index):
        self.band_index = band_index
        self._send_command("e", band_index)

    def set_volume(self, volume):
        self.volume = volume
        self._send_command("g", volume)


def print_busy():
    print("busy")

def print_idle():
    print("idle")

def main(args):
    app = QtGui.QApplication(args)

    wid = QtGui.QWidget()
    wid.resize(250, 150)
    wid.setWindowTitle('Simple')
    wid.show()

    d = CWDaemon()
    d.busy.connect(print_busy)
    d.idle.connect(print_idle)
    d.start()

    d.reset()

    d.send_text("vvvka")
    d.send_text("paris")
    d.send_text("paris")
    d.send_text("paris")
    d.send_text("*")

    QtCore.QTimer.singleShot(4000, lambda: d.abort())

    result = app.exec_()

    d.stop()

    sys.exit(result)

# run cwdaemon for testing: cwdaemon -yi -xs -n -d null
