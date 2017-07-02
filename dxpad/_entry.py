#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

from PySide import QtCore, QtGui

from . import _notepad

class EntryLine(QtCore.QObject):
    def __init__(self, notepad, max_note_length = 60, parent = None):
        QtCore.QObject.__init__(self, parent)
        self.notepad = notepad
        self.max_note_length = max_note_length
        self.text = ""

    @QtCore.Slot(str)
    def send_line(self):
        if self.is_command(self.text): return # TODO send to command
        self.notepad.add_line(self.text)
        self.text = ""

    @QtCore.Slot(str)
    def edit_line(self, text):
        self.text = text
        if self.is_command(text): return None
        if len(text) < self.max_note_length: return None
        tail = text
        while len(tail) > self.max_note_length:
            wrap_index = tail.rfind(" ")
            if wrap_index == -1:
                self.text = tail[:self.max_note_length]
                self.send_line()
                tail = tail[self.max_note_length:]
            else:
                self.text = tail[:wrap_index]
                self.send_line()
                tail = tail[wrap_index + 1:]

        self.text = tail
        return (self.text, len(self.text))

    def is_command(self, text):
        return text.startswith(":")
       
class EntryWidget(QtGui.QLineEdit):
    def __init__(self, entry_line, parent = None):
        QtGui.QLineEdit.__init__(self, parent)
        self.entry_line = entry_line

        self.returnPressed.connect(self.send_line)
        self.textEdited.connect(self.edit_line)

    def send_line(self):        
        self.entry_line.send_line()
        self.setText(self.entry_line.text)

    def edit_line(self, text):
        result = self.entry_line.edit_line(text)
        if not result: return
        self.setText(result[0])
        self.setCursorPosition(result[1])

    def keyPressEvent(self, e):
        if e.matches(QtGui.QKeySequence.MoveToNextLine):
            self.entry_line.notepad.move_cursor_down()
        elif e.matches(QtGui.QKeySequence.MoveToPreviousLine):
            self.entry_line.notepad.move_cursor_up()
        elif e.matches(QtGui.QKeySequence.SelectNextLine):
            self.entry_line.notepad.move_qso_end()
        elif e.matches(QtGui.QKeySequence.SelectPreviousLine):
            self.entry_line.notepad.move_qso_start()
        else:
            QtGui.QLineEdit.keyPressEvent(self, e)

class EntryWindow(QtGui.QWidget):
    def __init__(self, entry_line, parent = None):
        QtGui.QWidget.__init__(self, parent)

        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(EntryWidget(entry_line))
        self.setLayout(vbox)
        self.setWindowTitle("Entry")

@QtCore.Slot(object)
def print_line(line):
    print("line: " + str(line))

@QtCore.Slot(object)
def print_call(call):
    print("call: " + str(call))

def main(args):
    app = QtGui.QApplication(args)

    notepad = _notepad.Notepad()
    notepad.line_added.connect(print_line)
    notepad.call_added.connect(print_call)
    entry_line = EntryLine(notepad)

    win = EntryWindow(entry_line)
    win.resize(640, 50)
    win.show()

    result = app.exec_()
    sys.exit(result)

if __name__ == "__main__": main(sys.argv)