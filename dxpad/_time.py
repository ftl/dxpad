#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import time

def z(timestamp):
	return time.strftime("%H%MZ", time.gmtime(timestamp))
