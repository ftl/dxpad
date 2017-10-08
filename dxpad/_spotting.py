#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
import re
import telnetlib as tn
import Levenshtein as ls

from PySide import QtCore, QtGui

from . import _dxcc, _config, _grid, _callinfo, _time

FREQUENCY_WINDOW = 10.0 #kHz

class Spot:
    def __init__(self, ttl, call, frequency, time, source_call, source_grid):
        self.ttl = ttl
        self.call = call
        self.frequency = frequency
        self.time = time
        self.source_call = source_call
        self.source_grid = source_grid
        self.source_dxcc_info = None

    def __str__(self):
        return ("source({}, {}, {}) spot({}, {}, {}, {})"
            .format(
                self.source_call, self.source_grid, self.source_dxcc_info, 
                self.ttl, self.call, self.frequency, self.time))


class ClusterSpot(Spot):
    TTL = 300
    def __init__(
            self, call, frequency, time, source_call, source_grid, comment):
        Spot.__init__(
            self, self.TTL, call, frequency, time, source_call, source_grid)
        self.comment = comment

    def __str__(self):
        return Spot.__str__(self) + " cluster(" + self.comment + ")"


class RbnSpot(Spot):
    TTL = 60
    def __init__(
            self, call, frequency, time, source_call, source_grid, mode, snr, 
            speed, rbnType):
        Spot.__init__(
            self, self.TTL, call, frequency, time, source_call, source_grid)
        self.mode = mode
        self.snr = snr
        self.speed = speed
        self.rbnType = rbnType

    def __str__(self):
        return ("{} rbn(mode: {}, snr: {}, speed: {}, type: {})"
            .format(Spot.__str__(self), self.mode, self.snr, self.speed, 
                self.rbnType))

class TelnetClient:
    ENCODING = "latin_1"
    def __init__(self, hostname, port, call, password = ""):
        self.hostname = hostname
        self.port = port
        self.call = call
        self.password = password
        self.running = False

    def run(self, line_callback):
        try:
            telnet = tn.Telnet(self.hostname, self.port)
        except:
            print("Cannot connect to {}:{}".format(self.hostname, self.port))
            self.running = False
            return
        print("Connected to {}:{}".format(self.hostname, self.port))
        self.running = True

        buffer = ""
        while self.running:
            buffer += telnet.read_some().decode(self.ENCODING)
            while buffer.find("\n") != -1:
                line, buffer = buffer.split("\n", 1)
                line_callback(line)
            if buffer.endswith("Please enter your call: "):
                telnet.write(str(self.call + "\n").encode(self.ENCODING))
            if buffer.endswith("callsign: "):
                telnet.write(str(self.call + "\n").encode(self.ENCODING))
            if buffer.endswith("login: "):
                telnet.write(str(self.call + "\n").encode(self.ENCODING))
            if buffer.endswith("password: "):
                telnet.write(str(self.password + "\n").encode(self.ENCODING))

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


class FastTextfileClient:
    def __init__(self, filename):
        self.filename = filename

    def run(self, line_callback):
        with open(self.filename) as f:
            for line in f:
                line_callback(line)


class ClusterSpotter:
    _spot_expression = re.compile(r'DX de ([A-Z0-9/]+)(-.+?)?:?\s*([0-9]+\.[0-9]+)\s+([A-Z0-9/]+)\s+(.+?)\s([0-9]{4})Z(\s+([A-Z]{2}[0-9]{2}))?')
    _rbn_comment_expression = re.compile(r'([A-Z0-9]+)\s+([0-9]+) dB\s+([0-9]+) (WPM|BPS)\s+(.*)\s*')

    def __init__(self, client):
        self.client = client
        self.record = False

    def run(self, spot_callback):
        self.client.run(lambda line: self._line_received(line, spot_callback))

    def stop(self):
        self.client.stop()

    def is_running(self):
        return self.client.running

    def _line_received(self, line, spot_callback):
        if self.record:
            with open("rbn.txt", "a") as f:
                f.write(line)

        spot_match = self._spot_expression.match(line)
        if not spot_match:
            print(line)
            return

        if not _callinfo.Call.is_valid_call(spot_match.group(4)):
            print(line)
            return

        if not _callinfo.Call.is_valid_call(spot_match.group(1)):
            print(line)
            return
        
        call = _callinfo.Call(spot_match.group(4))
        frequency = float(spot_match.group(3))
        timestamp = time.time()
        source_call = _callinfo.Call(spot_match.group(1))
        source_grid = (_grid.Locator(spot_match.group(8))
                       if spot_match.group(8)
                       else None)
        comment = spot_match.group(5).strip()

        rbn_comment_match = self._rbn_comment_expression.match(comment)
        if rbn_comment_match:
            mode = rbn_comment_match.group(1)
            snr = float(rbn_comment_match.group(2))
            speed = rbn_comment_match.group(3)
            rbnType = rbn_comment_match.group(5)
            spot = RbnSpot(
                call, frequency, timestamp, source_call, source_grid, mode, 
                snr, speed, rbnType)
        else:
            spot = ClusterSpot(
                call, frequency, timestamp, source_call, source_grid, comment)
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


class DxSpot:
    def __init__(self, call, frequency, dxcc_info):
        self.call = call
        self.frequency = frequency
        self.dxcc_info = dxcc_info
        self.sources = set([])
        self.timeout = 0
        self.first_seen = time.time()
        self.last_seen = 0

    def __str__(self):
        return "{0:<10} on {1:>8.1f} kHz, timeout in {2:3.0f}, sources: {3:>2.0f}".format(str(self.call), self.frequency, self.timeout - time.time(), len(self.sources))

    def add_source(self, source_spot):
        self.sources.add(source_spot)
        if self.frequency != source_spot.frequency:
            self.frequency = (self.frequency + source_spot.frequency) / 2
        self.timeout = max(self.timeout, source_spot.time + source_spot.ttl)
        self.first_seen = min(self.first_seen, source_spot.time)
        self.last_seen = max(self.last_seen, source_spot.time)

    def merge(self, spot):
        self.sources.update(spot.sources)
        self.timeout = max(self.timeout, spot.timeout)
        self.first_seen = min(self.first_seen, spot.first_seen)
        self.last_seen = max(self.last_seen, spot.last_seen)


class SpotAggregator(QtCore.QObject):
    update_spots = QtCore.Signal(object)

    def __init__(self, dxcc, parent = None):
        QtCore.QObject.__init__(self, parent)
        self.dxcc = dxcc
        self.spots = {}
        self.spotting_threads = []

    @QtCore.Slot(object)
    def spot_received(self, incoming_spot):
        incoming_spot.source_dxcc_info = self.dxcc.find_dxcc_info(
            incoming_spot.source_call)

        if incoming_spot.call in self.spots:
            spots_by_call = self.spots[incoming_spot.call]
            spot = None
            for s in spots_by_call:
                if abs(s.frequency - incoming_spot.frequency) \
                    <= FREQUENCY_WINDOW:
                    spot = s
                    break

            if not spot:
                spot = DxSpot(
                    incoming_spot.call, incoming_spot.frequency, 
                    self.dxcc.find_dxcc_info(incoming_spot.call))
                spots_by_call.append(spot)
            spot.add_source(incoming_spot)

        else:
            spot = DxSpot(
                incoming_spot.call, incoming_spot.frequency, 
                self.dxcc.find_dxcc_info(incoming_spot.call))
            spot.add_source(incoming_spot)
            spots_by_call = [spot]

        self.spots[incoming_spot.call] = spots_by_call

    @QtCore.Slot()
    def cleanup_spots(self):
        now = time.time()
        active_spots = [spot for spots_by_call in list(self.spots.values()) 
            for spot in spots_by_call
            if now <= spot.timeout]

        spots_to_emit = sorted(active_spots, key= lambda spot: spot.frequency)
        spots_to_emit = self._merge_spots_with_similar_call(spots_to_emit)

        self.spots = self._group_spots_by_call(spots_to_emit)
        self.update_spots.emit(spots_to_emit)

    def _merge_spots_with_similar_call(self, spots):
        result = []
        window = []
        tail = spots

        while tail or window:
            window, tail = self._pop_frequency_window(window, tail)
            merge_candidates, window = self._extract_merge_candidates(window)
            merge_target = self._merge_spots(merge_candidates)
            if merge_target:
                result.append(merge_target)
        return result

    def _pop_frequency_window(self, current_window, spots):
        window = current_window
        tail = spots
        if window:
            lower_bound_frequency = window[0].frequency
        elif tail:
            lower_bound_frequency = tail[0].frequency
        else:
            return (window, tail)

        while tail:
            next_spot = tail[0]
            if next_spot.frequency - lower_bound_frequency <= FREQUENCY_WINDOW:
                window.append(tail.pop(0))
            else:
                break
        return window, tail

    def _extract_merge_candidates(self, spots):
        if not spots: return ([], [])
        remainder = spots
        seam = remainder.pop(0)
        merge_candidates = [seam]
        i = 0
        while i < len(remainder):
            spot = remainder[i]
            distance = ls.distance(seam.call.base_call, spot.call.base_call)
            if distance <= 1:
                merge_candidates.append(spot)
                remainder.pop(i)
            else:
                i += 1
        return merge_candidates, remainder

    def _merge_spots(self, spots):
        if not spots: return None
        merge_candidates = sorted(spots, key= lambda s: len(s.sources))
        merge_target = merge_candidates.pop()
        for spot in merge_candidates:
            merge_target.merge(spot)
        return merge_target

    def _group_spots_by_call(self, spots):
        grouped_spots = {}
        for spot in spots:
            if not spot.call in grouped_spots:
                grouped_spots[spot.call] = [spot]
            else:
                grouped_spots[spot.call].append(spot) 
        return grouped_spots

    def start_spotting(self, clusters, spotting_file = None):
        for c in clusters:
            st = SpottingThread.telnet(c.host, c.port, c.user, c.password)
            st.spot_received.connect(self.spot_received)
            st.start()
            self.spotting_threads.append(st)

        if spotting_file:
            st = SpottingThread.textfile(spotting_file)
            st.spot_received.connect(self.spot_received)
            st.start()
            self.spotting_threads.append(st)

    def stop_spotting(self):
        for st in self.spotting_threads:
            st.stop()
            st.wait()
        self.spotting_threads = []


@QtCore.Slot(object)
def print_spots(spots):
    print("Spots at {}:".format(_time.z(time.time())))
    print("\n".join([str(spot) for spot in spots]))
    print("")
    sys.stdout.flush()
    sys.stderr.flush()


def main(args):
    dxcc = _dxcc.DXCC()
    dxcc.load()

    textfileClient = FastTextfileClient("rbn.txt")
    spotter = ClusterSpotter(textfileClient)
    aggregator = SpotAggregator(dxcc)
    aggregator.update_spots.connect(print_spots)
    spotter.run(aggregator.spot_received)
    aggregator.cleanup_spots()


def main_(args):
    app = QtGui.QApplication(args)

    wid = QtGui.QWidget()
    wid.resize(250, 150)
    wid.setWindowTitle('Simple')
    wid.show()

    config = _config.load_config()

    dxcc = _dxcc.DXCC()
    dxcc.load()

    aggregator = SpotAggregator(dxcc)
    aggregator.update_spots.connect(print_spots)

    spot_cleanup_timer = QtCore.QTimer()
    spot_cleanup_timer.timeout.connect(aggregator.cleanup_spots)
    spot_cleanup_timer.start(1000)

    # st = SpottingThread.telnet("arcluster.reversebeacon.net", 7000, "dl3ney")
    # st.spotter.record = True
    st = SpottingThread.textfile("rbn.txt")
    st.spot_received.connect(aggregator.spot_received)
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

# WCY de DK0WCY-1 <12> : K=2 expK=0 A=13 R=12 SFI=72 SA=qui GMF=qui Au=no
