#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import unittest
sys.path.insert(0, os.path.abspath('..'))

import dxpad._contest as _contest

class SignalMonitor:
    signal_received = False
    signal_value = None

    def __init__(self, signal):
        signal.connect(self.signal_receiver)

    def signal_receiver(self, value = None):
        self.signal_received = True
        self.signal_value = value

class TestCurrentQso(unittest.TestCase):
    def test_create(self):
        qso = _contest.CurrentQso(_contest.Exchange())

    def test_next_increases_serial(self):
        qso = _contest.CurrentQso(_contest.Exchange())
        qso.next()
        self.assertEqual(qso.serial, 2)

    def test_next_updates_exchange_out(self):
        exchange = _contest.SerialExchange()
        qso = _contest.CurrentQso(exchange)
        qso.serial = 123
        qso.next()
        self.assertEqual(exchange.serial, 124)

    def test_next_clears_inputs(self):
        qso = _contest.CurrentQso(_contest.SerialExchange())
        qso.call = "the call"
        qso.exchange_in = "the exchange in"
        qso.call_valid = True
        qso.exchange_in_valid = True
        qso.complete = True
        qso.next()
        self.assertEqual(qso.call, "")
        self.assertEqual(qso.exchange_in, "")
        self.assertFalse(qso.call_valid)
        self.assertFalse(qso.exchange_in_valid)
        self.assertFalse(qso.complete)

    def test_next_emits_changed_invalid_and_incomplete(self):
        qso = _contest.CurrentQso(_contest.SerialExchange())
        qso.call_valid = True
        qso.exchange_in_valid = True
        qso.complete = True
        monitor_changed = SignalMonitor(qso.changed)
        monitor_call = SignalMonitor(qso.call_is_valid)
        monitor_exchange_in = SignalMonitor(qso.exchange_in_is_valid)
        monitor_complete = SignalMonitor(qso.completed)
        qso.next()
        self.assertTrue(monitor_changed.signal_received)
        self.assertTrue(monitor_call.signal_received)
        self.assertFalse(monitor_call.signal_value)
        self.assertTrue(monitor_exchange_in.signal_received)
        self.assertFalse(monitor_exchange_in.signal_value)
        self.assertTrue(monitor_complete.signal_received)
        self.assertFalse(monitor_complete.signal_value)

    def test_set_call_valid_emits_call_is_valid(self):
        qso = _contest.CurrentQso(_contest.Exchange())
        monitor = SignalMonitor(qso.call_is_valid)
        qso.set_call("N1")
        self.assertFalse(monitor.signal_received)
        qso.set_call("N1MM")
        self.assertTrue(monitor.signal_received)
        self.assertTrue(monitor.signal_value)

    def test_set_exchange_in_valid_emits_exchange_in_is_valid(self):
        qso = _contest.CurrentQso(_contest.Exchange())
        monitor = SignalMonitor(qso.exchange_in_is_valid)
        qso.set_exchange_in("1")
        self.assertTrue(monitor.signal_received)
        self.assertTrue(monitor.signal_value)


class TestSerialExchange(unittest.TestCase):
    def test_str_padding_with_zeros(self):
        exchange = _contest.SerialExchange()
        self.assertEqual(str(exchange), "599001")

    def test_str_padding_only_to_three_digits(self):
        exchange = _contest.SerialExchange()
        exchange.serial = 1000
        self.assertEqual(str(exchange), "5991000")

    def test_next_uses_serial_of_qso(self):
        exchange = _contest.SerialExchange()
        qso = _contest.CurrentQso(exchange)
        qso.serial = 123
        exchange.next(qso)
        self.assertEqual(exchange.serial, 123)

    def test_next_emits_changed(self):
        exchange = _contest.SerialExchange()
        monitor = SignalMonitor(exchange.changed)
        exchange.next(_contest.CurrentQso(exchange))
        self.assertTrue(monitor.signal_received)
