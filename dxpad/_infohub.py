#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import webbrowser

from PySide import QtCore, QtGui

from . import _dxcc, _grid, _location, _qrz, _hamqth, _callinfo, _time, \
              _config, _windowmanager

class Infohub(QtCore.QObject):
    info_changed = QtCore.Signal(object, object)
    locator_changed = QtCore.Signal(object)
    call_looked_up = QtCore.Signal(object)

    def __init__(
            self, dxcc, callbooks = [], own_call = _config.DEFAULT_CALL, 
            own_locator = _config.DEFAULT_LOCATOR, parent = None):
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
        if (info.postal_address 
                and (not existing_info.postal_address 
                    or len(existing_info.postal_address) 
                        < len(info.postal_address))):
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
        self.info_changed.emit(call, existing_info)
        self._emit_locator_changed(existing_info)

    def _emit_locator_changed(self, info):
        if info.locator:
            self.locator_changed.emit(info.locator)
        elif info.latlon:
            self.locator_changed.emit(_grid.Locator.from_lat_lon(info.latlon))

    @QtCore.Slot(object)
    def calls_seen(self, spots):
        for spot in spots:
            if spot.call in self:
                existing_info = self[spot.call]
                existing_info.last_seen = spot.last_seen
                existing_info.last_seen_frequency = spot.frequency
                existing_info.spot_sources = len(spot.sources)
                existing_info.touch()
                self.info_changed.emit(spot.call, existing_info)

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

    def _emit_lookup(self, call, info):
        self.call_looked_up.emit(call)
        self.info_changed.emit(call, info)
        self._emit_locator_changed(info)

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
        if not self.info: 
            self.label.setText("")    
            return
        self.call = info.call

        label_text = "<h1>{}</h1>".format(info.call)
        label_text += self._para(info.name)
        if info.postal_address:
            label_text += self._para(
                "<br>".join([s for s in info.postal_address if s != info.name]))

        if info.dxcc_info:
            tag_style = "color: white; background: gray;"
            label_text += self._div("".join([
                "<h3>{}</h3>".format(info.dxcc_info.name),
                self._para(" &nbsp; ".join([
                    self._span(
                        "{}"
                        .format(info.dxcc_info.continent), tag_style),
                    self._span(
                        "ITU {}"
                        .format(info.dxcc_info.itu_zone), tag_style),
                    self._span(
                        "CQ {}"
                        .format(info.dxcc_info.cq_zone), tag_style),
                    self._span(
                        "IOTA {}"
                        .format(info.iota) if info.iota else None, tag_style),
                    self._span(
                        "DOK {}"
                        .format(info.dok) if info.dok else None, tag_style)
                ]))
            ]))

        label_text += self._div("".join([
            self._para("Loc: {}".format(info.locator)),
            self._para("Lat/Lon: {}".format(info.latlon)),
            self._para(
                "Entfernung: {:.0f}km"
                .format(info.distance_to(self.own_locator))),
            self._para(
                "Richtung: {:.1f}°"
                .format(info.bearing_from(self.own_locator)))
        ]))

        if (info.qsl_service and len(info.qsl_service) > 0) or info.qsl_via:
            tag_style = "color: white; background: gray;"
            label_text += self._div("".join(
                [s for s in [
                    self._para(" &nbsp; ".join(
                        [self._span(s, tag_style) for s in info.qsl_service]
                    )) if info.qsl_service and len(info.qsl_service) > 0 else None,
                    self._para("QSL via: {}".format(info.qsl_via)) if info.qsl_via else None
            ] if s != None]))

        if info.qrz_id or info.hamqth_id:
            label_text += self._para(", ".join([s for s in [
                self._link("https://www.hamqth.com/{}", info.hamqth_id, "HamQTH"),
                self._link("https://qrz.com/db/{}", info.qrz_id, "qrz")
            ] if s != ""]))
        if info.email:
            label_text += self._para(
                self._link("mailto:{}", info.email, info.email))
        if info.last_seen:
            label_text += self._div(
                self._para("zuletzt um {0} auf {1:>8.1f} kHz ({2})"
                    .format(_time.z(info.last_seen),
                            info.last_seen_frequency,
                            info.spot_sources)))
        self.label.setText(label_text)

    def _div(self, content, style = "margin-top: 3px;"):
        return "<div style='{}'>{}</div>".format(style, content) if content else ""

    def _para(self, content, style = "margin: 0;"):
        return "<p style='{}'>{}</p>".format(style, content) if content else ""

    def _link(self, url_template, url_fillin, label):
        if not url_fillin: return ""
        url = url_template.format(url_fillin)
        return "<a href='{}'>{}</a>".format(url, label)

    def _span(self, content, style = ""):
        return "<span style='{}'>{}</span>".format(style, content) if content else ""

class InfohubWidget(QtGui.QWidget):
    def __init__(self, infohub, parent = None):
        QtGui.QWidget.__init__(self, parent)
        self.infohub = infohub
        self.infohub.call_looked_up.connect(self.show_info)
        self.infohub.info_changed.connect(self.update_info)

        self.info_widget = CallinfoWidget(None, None, self.infohub.own_locator)

        info_parent = QtGui.QVBoxLayout()
        info_parent.setContentsMargins(0, 0, 0, 0)
        info_parent.setSpacing(0)
        info_parent.setSizeConstraint(QtGui.QLayout.SetMinAndMaxSize)
        info_parent.addWidget(self.info_widget)
        info_parent.addStretch()
        
        frame = QtGui.QFrame()
        frame.setLayout(info_parent)
        scroll_area = QtGui.QScrollArea()
        scroll_area.setWidget(frame)

        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(scroll_area)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)
        self.setLayout(vbox)

    @QtCore.Slot(object)
    def show_info(self, call):
        self.info_widget.update_info(self.infohub[call])

    @QtCore.Slot(object, object)
    def update_info(self, call, info):
        if call == self.info_widget.call:
            self.info_widget.update_info(info)

class InfohubWindow(_windowmanager.ManagedWindow):
    def __init__(self, infohub, parent = None):
        _windowmanager.ManagedWindow.__init__(self, parent)
        self.setObjectName("infohub")
        self.infohub = infohub

        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(InfohubWidget(self.infohub))
        self.setLayout(vbox)
        self.setWindowTitle("Infohub")

def print_lookup(o):
    print("looked up: " + str(o))

def main(args):
    app = QtGui.QApplication(args)

    config = _config.load_config()
    dxcc = _dxcc.DXCC()
    dxcc.load()
    hamqth = _hamqth.AsyncHamQTH(config.hamqth.user, config.hamqth.password)
    qrz = _qrz.AsyncQrz(config.qrz.user, config.qrz.password)
    infohub = Infohub(dxcc, [hamqth, qrz], config.call, config.locator)
    infohub.call_looked_up.connect(print_lookup)
    infohub.locator_changed.connect(print_lookup)

    infohub_win = InfohubWindow(infohub)
    infohub_win.resize(300, 400)
    infohub_win.show()

    infohub.lookup_call(_callinfo.Call("dl3ny"))

    result = app.exec_()
    qrz.wait()
    hamqth.wait()

    sys.exit(result)
