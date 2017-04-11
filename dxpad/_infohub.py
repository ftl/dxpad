#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, webbrowser
from PySide import QtCore, QtGui

import _dxcc, _grid, _location, _qrz, _hamqth, _callinfo, _time, _config

class Infohub(QtCore.QObject):
	info_changed = QtCore.Signal(object, object)
	call_looked_up = QtCore.Signal(object)
	locator_looked_up = QtCore.Signal(object)

	def __init__(self, dxcc, callbooks = [], own_call = _config.DEFAULT_CALL, own_locator = _config.DEFAULT_LOCATOR, parent = None):
		QtCore.QObject.__init__(self, parent)
		self.callinfos = {}
		self.dxcc = dxcc
		self.callbooks = callbooks
		for callbook in self.callbooks:
			callbook.call_info.connect(self.add_info)
		self.own_call = own_call
		self.own_locator = own_locator

	def __len__(self):
		return len(self.callinfos)

	def __getitem__(self, key):
		return self.callinfos[key]

	def __setitem__(self, key, value):
		self.callinfos[key] = value

	def __delitem__(self, key):
		del self.callinfos[key]

	def __iter__(self):
		return self.callinfos

	def __reversed__(self):
		return reversed(self.callinfos)

	def __contains__(self, key):
		return key in self.callinfos

	@QtCore.Slot(object, object)
	def add_info(self, call, info):
		existing_info = self[call]
		if info.qrz_id:
			existing_info.qrz_id = info.qrz_id
		if info.hamqth_id:
			existing_info.hamqth_id = info.hamqth_id
		if not existing_info.name:
			existing_info.name = info.name
		if info.postal_address and (not existing_info.postal_address or len(existing_info.postal_address) < len(info.postal_address)):
			existing_info.postal_address = info.postal_address
		if not existing_info.postal_address:
			existing_info.postal_address = info.postal_address
		if not existing_info.email:
			existing_info.email = info.email
		if info.iota:
			existing_info.iota = info.iota
		if info.latlon:
			existing_info.latlon = info.latlon
		if info.locator:
			existing_info.locator = info.locator
		if info.qsl_via:
			existing_info.qsl_via = info.qsl_via
		if info.qsl_service:
			if existing_info.qsl_service:
				existing_info.qsl_service = external_info.qsl_service.union(info.qsl_service)
			else:
				existing_info.qsl_service = info.qsl_service
		existing_info.touch()
		self._emit_lookup(call, existing_info)

	def _emit_lookup(self, call, info):
		self.info_changed.emit(call, info)
		self.call_looked_up.emit(call)
		if info.locator:
			self.locator_looked_up.emit(info.locator)
		elif info.latlon:
			self.locator_looked_up.emit(_grid.Locator.from_lat_lon(info.latlon))		

	@QtCore.Slot(object)
	def lookup_call(self, call):
		if not call: return
		if call == self.own_call: return
		if call in self: 
			info = self[call]
			info.touch()
			self._emit_lookup(call, info)
			return

		info = _callinfo.Info(call)
		info.dxcc_info = self.dxcc.find_dxcc_info(call)
		if info.dxcc_info:
			info.latlon = info.dxcc_info.latlon
			info.locator = _grid.Locator.from_lat_lon(info.dxcc_info.latlon)
		self[call] = info
		self._emit_lookup(call, info)
		for callbook in self.callbooks:
			callbook.lookup_call(call)

class CallinfoWidget(QtGui.QWidget):
	def __init__(self, call, info, own_locator, parent = None):
		QtGui.QWidget.__init__(self, parent)
		self.call = call
		self.info = info
		self.own_locator = own_locator
		self.label = QtGui.QLabel()
		self.label.linkActivated.connect(webbrowser.open)
		vbox = QtGui.QVBoxLayout()
		vbox.addWidget(self.label)
		self.setLayout(vbox)
		self.update_info(info)

	def update_info(self, info):
		self.info = info
		label_text = u"<h1>{}</h1>".format(self.call)
		label_text += self._para(info.name)
		if info.postal_address:
			label_text += self._para(u"<br>".join(filter(lambda s: s != info.name, info.postal_address)))

		if info.dxcc_info:
			tag_style = u"color: white; background: gray;"
			label_text += self._div(u"".join([
				u"<h3>{}</h3>".format(info.dxcc_info.name),
				self._para(u" &nbsp; ".join([
					self._span(u"{}".format(info.dxcc_info.continent), tag_style),
					self._span(u"ITU {}".format(info.dxcc_info.itu_zone), tag_style),
					self._span(u"CQ {}".format(info.dxcc_info.cq_zone), tag_style),
					self._span(u"IOTA {}".format(info.iota) if info.iota else None, tag_style),
					self._span(u"DOK {}".format(info.dok) if info.dok else None, tag_style)
				]))
			]))

		label_text += self._div(u"".join([
			self._para(u"Loc: {}".format(info.locator)),
			self._para(u"Lat/Lon: {}".format(info.latlon)),
			self._para(u"Entfernung: {:.0f}km".format(info.distance_to(self.own_locator))),
			self._para(u"Richtung: {:.1f}°".format(info.bearing_from(self.own_locator)))
		]))

		if (info.qsl_service and len(info.qsl_service) > 0) or info.qsl_via:
			tag_style = u"color: white; background: gray;"
			label_text += self._div(u"".join(
				filter(lambda s: s != None, [
					self._para(u" &nbsp; ".join(
						map(lambda s: self._span(s, tag_style), info.qsl_service)
					)) if info.qsl_service and len(info.qsl_service) > 0 else None,
					self._para(u"QSL via: {}".format(info.qsl_via)) if info.qsl_via else None
			])))

		if info.qrz_id or info.hamqth_id:
			label_text += self._para(u", ".join(filter(lambda s: s != "", [
				self._link(u"https://www.hamqth.com/{}", info.hamqth_id, u"HamQTH"),
				self._link(u"https://qrz.com/db/{}", info.qrz_id, u"qrz")
			])))
		if info.email:
			label_text += self._para(self._link(u"mailto:{}", info.email, info.email))
		label_text += "<hr>"
		self.label.setText(label_text)

	def _div(self, content, style = u"margin-top: 3px;"):
		return u"<div style='{}'>{}</div>".format(style, content) if content else u""

	def _para(self, content, style = u"margin: 0;"):
		return u"<p style='{}'>{}</p>".format(style, content) if content else u""

	def _link(self, url_template, url_fillin, label):
		if not url_fillin: return u""
		url = url_template.format(url_fillin)
		return u"<a href='{}'>{}</a>".format(url, label)

	def _span(self, content, style = u""):
		return u"<span style='{}'>{}</span>".format(style, content) if content else u""

class InfohubWidget(QtGui.QWidget):
	def __init__(self, infohub, parent = None):
		QtGui.QWidget.__init__(self, parent)
		self.infohub = infohub
		self.infohub.info_changed.connect(self.update_info)

		self.info_widgets = {}

		self.info_parent = QtGui.QVBoxLayout()
		self.info_parent.setContentsMargins(0, 0, 0, 0)
		self.info_parent.setSpacing(0)
		self.info_parent.setSizeConstraint(QtGui.QLayout.SetMinAndMaxSize)
		self.info_parent.addStretch()
		
		frame = QtGui.QFrame()
		frame.setLayout(self.info_parent)
		self.scroll_area = QtGui.QScrollArea()
		self.scroll_area.setWidget(frame)
		self.scroll_area.verticalScrollBar().rangeChanged.connect(self._scroll_to_bottom)
		vbox = QtGui.QVBoxLayout()
		vbox.addWidget(self.scroll_area)
		vbox.setContentsMargins(0, 0, 0, 0)
		vbox.setSpacing(0)
		self.setLayout(vbox)

	@QtCore.Slot(int, int)
	def _scroll_to_bottom(self, min, max):
		self.scroll_area.verticalScrollBar().setValue(max)

	@QtCore.Slot(object, object)
	def update_info(self, call, info):
		if call in self.info_widgets:
			info_widget = self.info_widgets[call]
			info_widget.update_info(info)
			self.info_parent.removeWidget(info_widget)
		else:
			self._bound_widgets()
			info_widget = CallinfoWidget(call, info, self.infohub.own_locator)
			self.info_widgets[call] = info_widget
		self.info_parent.addWidget(info_widget)

	def _bound_widgets(self, boundary = 10):
		index = 0
		while len(self.info_widgets) >= boundary:
			widget_item = self.info_parent.itemAt(index)
			widget = widget_item.widget()
			if widget:
				self.info_parent.takeAt(index)
				del self.info_widgets[widget.call]
				widget.deleteLater()
			else:
				index += 1

class InfohubWindow(QtGui.QWidget):
    def __init__(self, infohub, parent = None):
        QtGui.QWidget.__init__(self, parent)
        self.infohub = infohub

        self.line = QtGui.QLineEdit(self)
        self.line.returnPressed.connect(self.lookup_call)

        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(InfohubWidget(self.infohub))
        vbox.addWidget(self.line)
        self.setLayout(vbox)
        self.setWindowTitle("Infohub")

    def lookup_call(self):
        self.infohub.lookup_call(_callinfo.Call(self.line.text()))
        self.line.setText("")

def print_lookup(o):
	print "looked up: " + str(o)

def main(args):
	app = QtGui.QApplication(args)

	config = _config.load_config()
	dxcc = _dxcc.DXCC()
	dxcc.load()
	hamqth = _hamqth.AsyncHamQTH(config.hamqth.user, config.hamqth.password)
	qrz = _qrz.AsyncQrz(config.qrz.user, config.qrz.password)
	infohub = Infohub(dxcc, [hamqth, qrz], config.call, config.locator)
	infohub.call_looked_up.connect(print_lookup)
	infohub.locator_looked_up.connect(print_lookup)

	infohub_win = InfohubWindow(infohub)
	infohub_win.resize(300, 400)
	infohub_win.show()

	result = app.exec_()
	qrz.wait()
	hamqth.wait()

	sys.exit(result)

if __name__ == "__main__": main(sys.argv)
