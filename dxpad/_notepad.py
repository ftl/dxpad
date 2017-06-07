#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, time, re, collections, math
from PySide import QtCore, QtGui

from . import _callinfo, _time

COLOR_TEXT = QtGui.QColor(0, 0, 0)
COLOR_DIVIDER = QtGui.QColor(150, 150, 150)
COLOR_TIMESTAMP = QtGui.QColor(0, 0, 0)
COLOR_BACKGROUND = QtGui.QColor(255, 255, 255)
COLOR_CURSOR = QtGui.QColor(129, 190, 247)
COLOR_QSO_BACKGROUND = QtGui.QColor(246, 227, 206)
COLOR_CALL = QtGui.QColor(150, 0, 0)

class Section:
    def __init__(self, kind, content, data = None):
        self.kind = kind
        self.content = content
        self.data = data

class NotedLine:
    def __init__(self, timestamp, sections):
        self.timestamp = timestamp
        self.sections = sections

    def __str__(self):
        return _time.z(self.timestamp) + ": " + "".join([s.content for s in self.sections])

class NotedQsos:
    class Qso(collections.namedtuple("QSO", "start end")):
        def __len__(self):
            return self.end - self.start + 1
        def __contains__(self, line):
            return self.start <= line and line <= self.end

    def __init__(self):
        self.qsos = []

    def __getitem__(self, index):
        return self.qsos[index]

    def __len__(self):
        return len(self.qsos)

    def __iter__(self):
        return self.qsos

    def insert_qso(self, line):
        index = self._find_insertion_index(line)
        if index < 0: return None
        new_qso = self.Qso(line, line)
        self.qsos.insert(index, new_qso)
        return new_qso

    def _find_insertion_index(self, line):
        return self._bisect_qsos(line, 0, len(self.qsos), lambda i, q: -1, lambda s: s)

    def is_in_qso(self, line):
        return self._find_qso(line)[1] != None

    def _find_qso(self, line):
        return self._bisect_qsos(line, 0, len(self.qsos), lambda i, q: (i, q), lambda s: (s, None))

    def _bisect_qsos(self, line, start, end, found, not_found):
        if start >= end: return not_found(start)
        pivot = (start + end) / 2
        qso = self.qsos[pivot]
        if line in qso: return found(pivot, qso)
        elif qso.start > line: return self._bisect_qsos(line, start, pivot, found, not_found)
        else: return self._bisect_qsos(line, pivot + 1, end, found, not_found) 

    def remove_qso(self, line):
        qso = self._find_qso(line)[1]
        self.qsos.remove(qso)

    def get_qso(self, line):
        return self._find_qso(line)[1]

    def get_qsos(self, start_line, end_line):
        start_index, start_qso = self._find_qso(start_line)
        if not start_qso:
            start_index, start_qso = self._find_qso_after(start_line)
        if not start_qso:
            return []
        end_index, end_qso = self._find_qso(end_line)
        if not end_qso:
            end_index, end_qso = self._find_qso_before(end_line) 
        if not end_qso:
            return []
        return self.qsos[start_index:end_index + 1]

    def move_qso_start(self, line):
        index, qso = self._find_qso(line)
        if not qso:
            index, qso = self._find_qso_after(line)
        if not qso:
            new_qso = self.Qso(line, line)
            self.qsos.insert(index, new_qso)
        else:
            new_qso = self.Qso(line, qso.end)
            self.qsos[index] = new_qso
        return new_qso

    def _find_qso_after(self, line):
        index = self._find_insertion_index(line)
        if index == len(self.qsos): return (index, None)
        return (index, self.qsos[index])

    def move_qso_end(self, line):
        index, qso = self._find_qso(line)
        if not qso:
            index, qso = self._find_qso_before(line)
        if not qso:
            new_qso = self.Qso(line, line)
            self.qsos.insert(index, new_qso)
        else:
            new_qso = self.Qso(qso.start, line)
            self.qsos[index] = new_qso
        return new_qso

    def _find_qso_before(self, line):
        index = self._find_insertion_index(line)
        if index == 0: return (index, None)
        return (index - 1, self.qsos[index - 1])

class Notepad(QtCore.QObject):
    line_added = QtCore.Signal(object)
    cursor_moved = QtCore.Signal(int)
    qso_changed = QtCore.Signal(object)
    call_added = QtCore.Signal(object)

    def __init__(self, parent = None):
        QtCore.QObject.__init__(self, parent)
        self.lines = []
        self.qsos = NotedQsos()
        self.cursor = -1

    def __len__(self):
        return len(self.lines)

    def add_line(self, raw_text):
        if len(raw_text.strip()) == 0: return
        sections = []
        next_char = 0
        for match in _callinfo.Call.find_all(raw_text, lambda m: m):
            match_start = match.start()
            match_end = match.end()
            if match_start > next_char:
                sections.append(Section("text", raw_text[next_char:match_start]))
            call = _callinfo.Call(raw_text[match_start:match_end])
            sections.append(Section("call", str(call), call))
            self.call_added.emit(call)
            next_char = match.end(0)
        if next_char < len(raw_text):
            sections.append(Section("text", raw_text[next_char:]))

        line = NotedLine(time.time(), sections)
        self.lines.append(line)
        self.line_added.emit(line)

    def move_cursor_up(self):
        last_cursor = self.cursor
        if self.cursor == -1:
            self.cursor = len(self) - 1
        else:
            self.cursor = max(0, self.cursor - 1)
        if last_cursor != self.cursor:
            self.cursor_moved.emit(self.cursor)

    def move_cursor_down(self):
        last_cursor = self.cursor
        if self.cursor == len(self) - 1 or self.cursor == -1:
            self.cursor = -1
        else:
            self.cursor += 1
        if last_cursor != self.cursor:
            self.cursor_moved.emit(self.cursor)

    def move_cursor_to(self, line_index):
        last_cursor = self.cursor
        if line_index < 0:
            self.cursor = -1
        else:
            self.cursor = min(line_index, len(self) - 1)
        if last_cursor != self.cursor:
            self.cursor_moved.emit(self.cursor)

    def is_cursor_line(self, line):
        if self.cursor == -1: return False
        return line == self.lines[self.cursor]

    def insert_qso(self):
        if self.cursor == -1: return
        qso = self.qsos.insert_qso(self.cursor)
        self.qso_changed.emit(qso)

    def remove_qso(self):
        if self.cursor == -1: return
        self.qsos.remove_qso(self.cursor)
        self.qso_changed.emit(None)

    def move_qso_start(self):
        if self.cursor == -1: return
        qso = self.qsos.move_qso_start(self.cursor)
        self.qso_changed.emit(qso)

    def move_qso_end(self):
        if self.cursor == -1: return
        qso = self.qsos.move_qso_end(self.cursor)
        self.qso_changed.emit(qso)

    def get_qso(self):
        if self.cursor == -1: return None
        return self.qsos.get_qso(self.cursor)

    def get_qsos(self, start_line, end_line):
        return self.qsos.get_qsos(start_line, end_line)

    def is_line_in_qso(self, line_index):
        return self.qsos.is_in_qso(line_index)

class _NotepadPainter:
    def __init__(self, painter, widget):
        self.painter = painter
        self.widget = widget
        self.size = widget.size()
        self.line_height = painter.fontMetrics().boundingRect("Hg").height() + 2
        self.visible_lines = math.floor((self.size.height() - 2) / self.line_height)
        self.timestamp_column_right = self.text_width("MMMMZ")
        self.divider_line_x = self.timestamp_column_right + 2
        self.content_column_left = self.timestamp_column_right + 4
        self.clip_visible_lines_rect = QtCore.QRect(0, 1, self.size.width(), self.visible_lines * self.line_height)
        self.clip_all_rect = QtCore.QRect(0, 0, self.size.width(), self.size.height())

    def text_width(self, text):
        return self.painter.fontMetrics().width(text)

    def content_line_rect(self, line_index):
        return QtCore.QRect(self.content_column_left, self.line_top(line_index), self.size.width() - self.content_column_left - 1, self.line_height)

    def timestamp_line_rect(self, line_index):
        return QtCore.QRect(0, self.line_top(line_index), self.timestamp_column_right, self.line_height)

    def line_top(self, line_index):
        return self.line_height * line_index + 1

    def text_rect(self, line_rect):
        return QtCore.QRect(line_rect.x() + 2, line_rect.y() + 1, line_rect.width() - 4, line_rect.height() - 2)

    def clip_visible_lines(self):
        self.painter.setClipRect(self.clip_visible_lines_rect)

    def clip_all(self):
        self.painter.setClipRect(self.clip_all_rect)

    def draw_background(self):
        self.painter.fillRect(QtCore.QRect(0, 0, self.size.width(), self.size.height()), COLOR_BACKGROUND)

    def draw_divider(self):
        self.painter.setPen(COLOR_DIVIDER)
        self.painter.drawLine(self.divider_line_x, 0, self.divider_line_x, self.size.height());

    def draw_timestamp(self, line_index, text, divider_above):
        line_rect = self.timestamp_line_rect(line_index)
        text_rect = self.text_rect(line_rect)
        if divider_above:
            self.painter.setPen(COLOR_DIVIDER)
            self.painter.drawLine(line_rect.x(), line_rect.y(), self.divider_line_x - line_rect.x(), line_rect.y())
        self.painter.setPen(COLOR_TIMESTAMP)
        self.painter.drawText(text_rect, QtCore.Qt.AlignRight, text)

    def draw_content(self, line_index, sections, in_qso):
        line_rect = self.content_line_rect(line_index)
        text_rect = self.text_rect(line_rect)
        if in_qso:
            self.painter.fillRect(line_rect, COLOR_QSO_BACKGROUND)

        text_colors = {"text": COLOR_TEXT, "call": COLOR_CALL}
        x = text_rect.x()
        y = text_rect.y()
        for section in sections:
            section_rect = self.painter.fontMetrics().boundingRect(section.content)
            section_rect.moveTo(x, y)
            section_rect.setWidth(self.text_width(section.content))
            if section.kind in text_colors:
                text_color = text_colors[section.kind]
            else:
                text_color = COLOR_TEXT
            self.painter.setPen(text_color)
            self.painter.drawText(section_rect, QtCore.Qt.AlignLeft, section.content)
            x += section_rect.width()

    def draw_qso_frame(self, start_index, end_index):
        start_line_rect = self.content_line_rect(start_index)
        end_line_rect = self.content_line_rect(end_index)
        rect = QtCore.QRect(start_line_rect.x(), start_line_rect.y(), start_line_rect.width(), end_line_rect.y() + end_line_rect.height() - start_line_rect.y() - 1)
        pen = QtGui.QPen(COLOR_DIVIDER)
        pen.setWidth(2)
        self.painter.setPen(pen)
        self.clip_visible_lines()
        self.painter.drawRect(rect)
        self.clip_all()

    def draw_cursor(self, line_index):
        line_rect = self.content_line_rect(line_index)
        pen = QtGui.QPen(COLOR_CURSOR)
        pen.setWidth(2)
        self.painter.setPen(pen)
        self.painter.drawRect(line_rect)        

class _PlainNotepadWidget(QtGui.QWidget):
    update_visible_lines = QtCore.Signal(int)
    line_clicked = QtCore.Signal(int)

    def __init__(self, notepad, parent = None):
        QtGui.QWidget.__init__(self, parent)
        self.notepad = notepad
        self.visible_lines = 0
        self.line_height = 0
        self.stick_to_bottom = True
        self.bottom_line = -1

    def scroll_to_bottom(self):
        self.stick_to_bottom = True
        self.bottom_line = -1
        self.repaint()

    def scroll_to_line(self, line):
        self.stick_to_bottom = False
        self.bottom_line = line
        self.repaint()

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        self.draw_widget(painter)
        painter.end()

    def draw_widget(self, painter):
        notepad_painter = _NotepadPainter(painter, self)

        notepad_painter.draw_background()
        notepad_painter.draw_divider()

        last_timestamp = ""
        if self.stick_to_bottom:
            top_line = len(self.notepad) - notepad_painter.visible_lines
            bottom_line = len(self.notepad) - 1
        else:
            top_line = self.bottom_line - notepad_painter.visible_lines + 1
            bottom_line = self.bottom_line
        lines = self.notepad.lines[max(0, top_line):bottom_line + 1]
        line_index = max(0, -top_line)
        for line in lines:
            timestamp = _time.z(line.timestamp)
            if timestamp != last_timestamp:
                notepad_painter.draw_timestamp(line_index, timestamp, last_timestamp != "")
                last_timestamp = timestamp

            line_in_qso = self.notepad.is_line_in_qso(line_index + top_line)
            notepad_painter.draw_content(line_index, line.sections, line_in_qso)
            line_index += 1

        for qso in self.notepad.get_qsos(max(0, top_line), bottom_line):
            notepad_painter.draw_qso_frame(qso.start - top_line, qso.end - top_line)

        if self.notepad.cursor >= max(0, top_line) and self.notepad.cursor <= bottom_line:
            notepad_painter.draw_cursor(self.notepad.cursor - top_line)

        self.line_height = notepad_painter.line_height
        last_visible_lines = self.visible_lines
        self.visible_lines = notepad_painter.visible_lines
        if self.visible_lines != last_visible_lines:
            self.update_visible_lines.emit(self.visible_lines)

    def mousePressEvent(self, e):
        if self.line_height <= 0: 
            e.ignore()
            return
        bottom_line = len(self.notepad) - 1 if self.stick_to_bottom else self.bottom_line
        tail = 1 #self.size().height() % self.line_height
        line_on_page = (e.y() - tail) / self.line_height
        line_index = bottom_line - self.visible_lines + line_on_page + 1
        if line_index < 0: 
            e.ignore()
            return
        self.line_clicked.emit(line_index)

class NotepadWidget(QtGui.QFrame):
    def __init__(self, notepad, parent = None):
        QtGui.QFrame.__init__(self, parent)
        self.notepad = notepad
        self.notepad.line_added.connect(self._line_added)
        self.notepad.cursor_moved.connect(self._cursor_moved)
        self.notepad.qso_changed.connect(self._qso_changed)

        self.plain_widget = _PlainNotepadWidget(self.notepad, self)
        self.plain_widget.update_visible_lines.connect(self._update_visible_lines)
        self.plain_widget.line_clicked.connect(self._line_clicked)

        self.scroll_bar = QtGui.QScrollBar(QtCore.Qt.Orientation.Vertical, self)
        self.scroll_bar.setMinimum(0)
        self.scroll_bar.setMaximum(len(notepad))
        self.scroll_bar.setPageStep(0)
        self.scroll_bar.valueChanged[int].connect(self._scrolled)

        hbox = QtGui.QHBoxLayout(self)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(0)
        hbox.addWidget(self.plain_widget)
        hbox.addWidget(self.scroll_bar)
        self.setLayout(hbox)

        self.setFrameStyle(QtGui.QFrame.WinPanel | QtGui.QFrame.Sunken)
        self.setLineWidth(1)

    def _line_added(self, line):
        self._update_scroll_bar(len(self.notepad), self.scroll_bar.pageStep(), True)
        self.plain_widget.scroll_to_bottom()

    @QtCore.Slot(int)
    def _update_visible_lines(self, visible_lines):
        self._update_scroll_bar(len(self.notepad), visible_lines, False)

    def _update_scroll_bar(self, lines, visible_lines, stick_to_bottom):
        was_at_bottom = self.at_bottom()
        self.scroll_bar.setPageStep(visible_lines)
        self.scroll_bar.setMaximum(max(0, lines - visible_lines))
        if was_at_bottom or stick_to_bottom:
            self.scroll_bar.setValue(self.scroll_bar.maximum())

    def at_bottom(self):
        return self.scroll_bar.value() == self.scroll_bar.maximum()

    def wheelEvent(self, e):
        self.scroll_bar.wheelEvent(e)

    @QtCore.Slot(int)
    def _scrolled(self, value):
        if self.at_bottom():
            self.plain_widget.scroll_to_bottom()
        else:
            bottom_line = value + self.scroll_bar.pageStep() - 1
            self.plain_widget.scroll_to_line(bottom_line)

    @QtCore.Slot(int)
    def _cursor_moved(self, value):
        if value == -1:
            self.scroll_bar.setValue(self.scroll_bar.maximum())
            self.plain_widget.scroll_to_bottom()
        elif value < self.scroll_bar.value():
            self.scroll_bar.setValue(value)
        elif value >= self.scroll_bar.value() + self.scroll_bar.pageStep():
            self.scroll_bar.setValue(value - self.scroll_bar.pageStep() + 1)
        else:
            self.plain_widget.repaint()

    @QtCore.Slot(object)
    def _qso_changed(self, qso):
        self.plain_widget.repaint()

    @QtCore.Slot(int)
    def _line_clicked(self, line_index):
        self.notepad.move_cursor_to(line_index)

class NotepadWindow(QtGui.QWidget):
    def __init__(self, notepad, parent = None):
        QtGui.QWidget.__init__(self, parent)

        self.notepad = notepad

        self.notepad_widget = NotepadWidget(notepad)
        self.line = QtGui.QLineEdit()
        self.line.returnPressed.connect(self.add_line_to_notepad)

        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.notepad_widget)
        vbox.addWidget(self.line)
        self.setLayout(vbox)
        
        self.setWindowTitle("Notepad")

    def add_line_to_notepad(self):        
        self.notepad.add_line(self.line.text())
        self.line.setText("")

    def keyPressEvent(self, e):
        if e.matches(QtGui.QKeySequence.MoveToNextLine):
            self.notepad.move_cursor_down()
        elif e.matches(QtGui.QKeySequence.MoveToPreviousLine):
            self.notepad.move_cursor_up()
        elif e.matches(QtGui.QKeySequence.SelectNextLine):
            self.notepad.move_qso_end()
        elif e.matches(QtGui.QKeySequence.SelectPreviousLine):
            self.notepad.move_qso_start()
        else:
            e.ignore()

@QtCore.Slot(object)
def print_added_calls(call):
    print("call added: " + str(call))

def main(args):
    app = QtGui.QApplication(args)

    notepad = Notepad()
    notepad.call_added.connect(print_added_calls)

    win = NotepadWindow(notepad)
    win.resize(640, 480)
    win.show()

    result = app.exec_()
    sys.exit(result)

if __name__ == "__main__": main(sys.argv)
