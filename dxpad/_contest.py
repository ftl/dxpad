#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

from PySide import QtCore, QtGui

from . import _cwdaemon, _callinfo, _config

class Qso:
    def __init__(self, nr, call, frequency, mode, exchange_in, exchange_out):
        self.nr = nr
        self.call = call
        self.frequency = frequency
        self.mode = mode
        self.exchange_in = exchange_in
        self.exchange_out = exchange_out


class Keyer(QtCore.QObject):
    def __init__(self, cw, parent = None):
        QtCore.QObject.__init__(self, parent)
        self.cw = cw
        self.own_call = ""
        self.dx_call = ""
        self.exchange_out = ""
        self.question = ""
        self.last_text = ""

    @QtCore.Slot(str)
    def set_dx_call(self, dx_call):
        self.dx_call = dx_call

    @QtCore.Slot(str)
    def set_question(self, question):
        self.question = question

    @QtCore.Slot()
    def send_own_call(self):
        self._send_text(str(self.own_call))

    @QtCore.Slot()
    def send_dx_call(self):
        self._send_text(str(self.dx_call))

    @QtCore.Slot()
    def send_exchange_out(self):
        self._send_text(self._to_cut_numbers(str(self.exchange_out)))

    @QtCore.Slot()
    def send_question(self):
        self._send_text("{}?".format(self.question))

    @QtCore.Slot()
    def repeat_last_text(self):
        self._send_text(self.last_text)

    @QtCore.Slot()
    def send_tu(self):
        self._send_text("tu")

    @QtCore.Slot()
    def send_agn(self):
        self._send_text("agn")

    @QtCore.Slot()
    def send_cq(self):
        self._send_text("cq {} ++++test----".format(self.own_call))

    def _send_text(self, text):
        self.last_text = text
        self.cw.send_text(text)

    def _to_cut_numbers(self, raw):
        replacements = {
            "0": "T",
            #"1": "A",
            #"2": "U",
            #"3": "V",
            #"5": "E",
            #"7": "G",
            #"8": "D",
            "9": "N",
        }
        cut = ""
        for c in raw:
            if c in replacements:
                cut += replacements[c]
            else:
                cut += c
        return cut


class ContestWidget(QtGui.QFrame):
    def __init__(self, keyer, parent = None):
        QtGui.QFrame.__init__(self, parent)
        self.keyer = keyer

        self.call_label = QtGui.QLabel("Call", self)
        self.call_input = QtGui.QLineEdit(self)

        self.exchange_in_label = QtGui.QLabel("IN", self)
        self.exchange_in_input = QtGui.QLineEdit(self)

        self.exchange_out_label = QtGui.QLabel("OUT", self)
        self.exchange_out_input = QtGui.QLineEdit(self)
        self.exchange_out_input.setEnabled(False)

        self.question_label = QtGui.QLabel("?", self)
        self.question_input = QtGui.QLineEdit(self)

        self.cq_button = QtGui.QPushButton("F1: CQ", self)
        self.exchange_out_button = QtGui.QPushButton("F2: Xchg OUT", self)
        self.tu_button = QtGui.QPushButton("F3: tu", self)
        self.own_call_button = QtGui.QPushButton("F4: {}".format(keyer.own_call), self)
        self.dx_call_button = QtGui.QPushButton("F5: their call", self)
        self.repeat_button = QtGui.QPushButton("F6: Repeat", self)
        self.question_button = QtGui.QPushButton("F7: ?", self)
        self.agn_button = QtGui.QPushButton("F8: agn", self)

        grid = QtGui.QGridLayout(self)
        grid.addWidget(self.call_label, 0, 0)
        grid.addWidget(self.call_input, 1, 0)
        grid.addWidget(self.exchange_in_label, 0, 1)
        grid.addWidget(self.exchange_in_input, 1, 1)
        grid.addWidget(self.exchange_out_label, 0, 2)
        grid.addWidget(self.exchange_out_input, 1, 2)
        grid.addWidget(self.question_label, 0, 3)
        grid.addWidget(self.question_input, 1, 3)
        grid.addWidget(self.cq_button, 2, 0)
        grid.addWidget(self.exchange_out_button, 2, 1)
        grid.addWidget(self.tu_button, 2, 2)
        grid.addWidget(self.own_call_button, 2, 3)
        grid.addWidget(self.dx_call_button, 3, 0)
        grid.addWidget(self.repeat_button, 3, 1)
        grid.addWidget(self.question_button, 3, 2)
        grid.addWidget(self.agn_button, 3, 3)
        grid.setRowStretch(4, 1)
        self.setLayout(grid)

        self.cq_button.clicked.connect(keyer.send_cq)
        self.exchange_out_button.clicked.connect(keyer.send_exchange_out)
        self.tu_button.clicked.connect(keyer.send_tu)
        self.own_call_button.clicked.connect(keyer.send_own_call)
        self.dx_call_button.clicked.connect(keyer.send_dx_call)
        self.repeat_button.clicked.connect(keyer.repeat_last_text)
        self.question_button.clicked.connect(keyer.send_question)
        self.agn_button.clicked.connect(keyer.send_agn)

        self.call_input.textChanged.connect(keyer.set_dx_call)
        self.question_input.textChanged.connect(keyer.set_question)

        self._shortcut("F1", keyer.send_cq)
        self._shortcut("F2", keyer.send_exchange_out)
        self._shortcut("F3", keyer.send_tu)
        self._shortcut("F4", keyer.send_own_call)
        self._shortcut("F5", keyer.send_dx_call)
        self._shortcut("F6", keyer.repeat_last_text)
        self._shortcut("F7", keyer.send_question)
        self._shortcut("F8", keyer.send_agn)
        self._shortcut("Ctrl+1", self.call_input.setFocus)
        self._shortcut("Ctrl+2", self.exchange_in_input.setFocus)
        self._shortcut("Ctrl+3", self.question_input.setFocus)

    def _shortcut(self, key, action):
        QtGui.QShortcut(QtGui.QKeySequence(key), self).activated.connect(action)        


class ContestWindow(QtGui.QWidget):
    def __init__(self, keyer, parent = None):
        QtGui.QWidget.__init__(self, parent)
        self.keyer = keyer

        self.contest_widget = ContestWidget(keyer, self)

        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.contest_widget)
        self.setLayout(vbox)

        self.setWindowTitle("Contest")


def main(args):
    config = _config.load_config()

    cw = _cwdaemon.CWDaemon()
    keyer = Keyer(cw)
    keyer.own_call = config.call
    keyer.exchange_out = "599001"

    app = QtGui.QApplication(args)

    window = ContestWindow(keyer)
    window.resize(640, 480)
    window.show()

    cw.start()

    result = app.exec_()

    cw.stop()

    sys.exit(result)
