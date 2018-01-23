#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

from PySide import QtCore, QtGui

from . import _cwdaemon, _callinfo, _config

COLOR_INVALID_CALL = QtGui.QColor(255, 255, 255)
COLOR_VALID_CALL = QtGui.QColor(255, 129, 129)

class LoggedQso:
    def __init__(self, serial, call, frequency, mode, exchange_in, exchange_out):
        self.serial = serial
        self.call = call
        self.frequency = frequency
        self.mode = mode
        self.exchange_in = exchange_in
        self.exchange_out = exchange_out


class CurrentQso(QtCore.QObject):
    changed = QtCore.Signal()
    call_is_valid = QtCore.Signal(bool)
    exchange_in_is_valid = QtCore.Signal(bool)
    completed = QtCore.Signal(bool)

    def __init__(self, exchange_out, parent = None):
        QtCore.QObject.__init__(self, parent)
        self.serial = 1
        self.exchange_out = exchange_out
        self._clear()
        self.call_valid = False
        self.exchange_in_valid = False
        self.complete = False

    QtCore.Slot()
    def _clear(self):
        self.call = ""
        self.frequency = ""
        self.mode = ""
        self.exchange_in = ""

    QtCore.Slot(int)
    def set_serial(self, serial):
        self.serial = serial
        self.exchange_out.next(self)
        self.changed.emit()
        self._check_complete()
                
    QtCore.Slot(str)
    def set_call(self, call):
        old_call = self.call
        self.call = call
        if old_call != self.call:
            self.changed.emit()
        self._check_complete()

    QtCore.Slot(str)
    def set_exchange_in(self, exchange_in):
        old_exchange_in = self.exchange_in
        self.exchange_in = exchange_in
        if old_exchange_in != self.exchange_in:
            self.changed.emit()
        self._check_complete()

    QtCore.Slot()
    def next(self):
        self.serial += 1
        self.exchange_out.next(self)
        self._clear()
        self.changed.emit()
        self._check_complete()

    def _check_complete(self):
        self.call_valid = self._emit_on_change(self.call_is_valid,
            self.call_valid, 
            _callinfo.Call.is_valid_call(self.call))

        self.exchange_in_valid = self._emit_on_change(self.exchange_in_is_valid,
            self.exchange_in_valid, 
            len(self.exchange_in) > 0)

        self.complete = self._emit_on_change(self.completed, 
            self.complete, 
            self.call_valid and self.exchange_in_valid)

    def _emit_on_change(self, signal, old_value, new_value):
        if old_value != new_value:
            signal.emit(new_value)
        return new_value


class Exchange(QtCore.QObject):
    changed = QtCore.Signal(str)

    def __init__(self, parent = None):
        QtCore.QObject.__init__(self, parent)

    @QtCore.Slot(object)
    def next(self, qso):
        pass


class RstExchange(Exchange):
    def __init__(self, parent = None):
        Exchange.__init__(self, parent)
        self.rst = "599"

    def __repr__(self):
        return "RstExchange({})".format(self.rst)

    def __str__(self):
        return "{0}".format(self.rst)


class SerialExchange(Exchange):
    def __init__(self, parent = None):
        Exchange.__init__(self, parent)
        self.rst = "599"
        self.serial = 1

    def __repr__(self):
        return "SerialExchange({}, {})".format(self.rst, self.serial)

    def __str__(self):
        return "{0}{1:03d}".format(self.rst, self.serial)

    @QtCore.Slot(object)
    def next(self, qso):
        self.serial = qso.serial
        self.changed.emit(str(self))


class Keyer(QtCore.QObject):
    def __init__(self, cw, exchange_out, parent = None):
        QtCore.QObject.__init__(self, parent)
        self.cw = cw
        self.own_call = ""
        self.dx_call = ""
        self.exchange_out = exchange_out
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
        self._send_text(self._cut_numbers(str(self.exchange_out)))

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

    def _cut_numbers(self, raw):
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
    def __init__(self, keyer, qso, parent = None):
        QtGui.QFrame.__init__(self, parent)
        self.keyer = keyer
        self.qso = qso

        self.call_label = QtGui.QLabel("Call", self)
        self.call_input = QtGui.QLineEdit(self)

        self.exchange_in_label = QtGui.QLabel("IN", self)
        self.exchange_in_input = QtGui.QLineEdit(self)

        self.exchange_out_label = QtGui.QLabel("OUT", self)
        self.exchange_out_input = QtGui.QLineEdit(str(self.qso.exchange_out), self)
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

        self.log_button = QtGui.QPushButton("Log", self)
        self.log_button.setEnabled(qso.complete)
        self.clear_button = QtGui.QPushButton("Clear", self)

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
        grid.addWidget(self.log_button, 4, 0, 1, 2)
        grid.addWidget(self.clear_button, 4, 2, 1, 2)

        grid.setRowStretch(5, 1)
        self.setLayout(grid)

        self.cq_button.clicked.connect(keyer.send_cq)
        self.exchange_out_button.clicked.connect(keyer.send_exchange_out)
        self.tu_button.clicked.connect(keyer.send_tu)
        self.own_call_button.clicked.connect(keyer.send_own_call)
        self.dx_call_button.clicked.connect(keyer.send_dx_call)
        self.repeat_button.clicked.connect(keyer.repeat_last_text)
        self.question_button.clicked.connect(keyer.send_question)
        self.agn_button.clicked.connect(keyer.send_agn)

        self.log_button.clicked.connect(self.log)
        self.clear_button.clicked.connect(self.clear)

        self.call_input.textChanged.connect(keyer.set_dx_call)
        self.call_input.textChanged.connect(qso.set_call)
        self.exchange_in_input.textChanged.connect(qso.set_exchange_in)
        self.question_input.textChanged.connect(keyer.set_question)

        self.qso.exchange_out.changed.connect(self.exchange_out_input.setText)
        self.qso.completed.connect(self.log_button.setEnabled)

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
        self._shortcut("Ctrl+Enter", self.log)
        self._shortcut("Shift+Esc", self.clear)

    def _shortcut(self, key, action):
        QtGui.QShortcut(QtGui.QKeySequence(key), self).activated.connect(action)

    def _update_input_from_qso(self):
        self.call_input.setText(self.qso.call)
        self.exchange_in_input.setText(self.qso.exchange_in)

    def _restart_input(self):
        self.question_input.setText("")
        self.call_input.setFocus()

    def log(self):
        if not self.log_button.isEnabled(): 
            return
        self.qso.next()
        self._update_input_from_qso()
        self._restart_input()

    def clear(self):
        self.qso.set_call("")
        self.qso.set_exchange_in("")
        self._update_input_from_qso()
        self._restart_input()


class ContestWindow(QtGui.QWidget):
    def __init__(self, keyer, qso, parent = None):
        QtGui.QWidget.__init__(self, parent)

        self.contest_widget = ContestWidget(keyer, qso, self)

        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.contest_widget)
        self.setLayout(vbox)

        self.setWindowTitle("Contest")


def main(args):
    config = _config.load_config()

    cw = _cwdaemon.CWDaemon()
    exchange_out = SerialExchange()
    qso = CurrentQso(exchange_out)
    keyer = Keyer(cw, exchange_out)
    keyer.own_call = config.call

    app = QtGui.QApplication(args)

    window = ContestWindow(keyer, qso)
    window.resize(640, 480)
    window.show()

    cw.start()

    result = app.exec_()

    cw.stop()

    sys.exit(result)
