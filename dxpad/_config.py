#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, os
from PySide import QtCore

import _grid, _callinfo

DEFAULT_CALL = "dl0aaa"
DEFAULT_LOCATOR = "JO51aa"

"""
Clusters for testing:
{ "host": "arcluster.reversebeacon.net", "port": "7000", "user": "dl0aaa", "password": "" },
{ "host": "db0ovp.de", "port": "4111", "user": "dl0aaa", "password": "" },
{ "host": "dxc.db0hst.de", "port": "8005", "user": "dl0aaa", "password": "" }
"""

def make_config_dir():
	path = os.path.expanduser("~/.config/dxpad/")
	if not os.path.exists(path):
		os.makedirs(path)
	return path

def filename(name):
	return make_config_dir() + name

class Account:
	def __init__(self, user, password = None):
		self.user = unicode(user).encode("utf-8")
		if password:
			self.password = unicode(password).encode("utf-8")
		else:
			self.password = None

class Cluster(Account):
	def __init__(self, host, port, user, password = None):
		Account.__init__(self, user, password)
		self.host = unicode(host).encode("utf-8")
		self.port = int(port)

class Config:
	def __init__(self):
		self.filename = filename("config.ini")
		self.settings = QtCore.QSettings(self.filename, QtCore.QSettings.IniFormat)
		self.call = _callinfo.Call(self.settings.value("call", DEFAULT_CALL))
		self.locator = _grid.Locator(self.settings.value("locator", DEFAULT_LOCATOR))
		self.clusters = self.get_clusters()
		self.hamqth = self.get_account("hamqth")
		self.qrz = self.get_account("qrz")

	def get_clusters(self):
		clusters = []
		size = self.settings.beginReadArray("clusters")
		for i in range(size):
			self.settings.setArrayIndex(i)
			host = self.settings.value("host", "arcluster.reversebeacon.net")
			port = int(self.settings.value("port", 7000))
			user = self.settings.value("user", self.call)
			password = self.settings.value("password", None)
			clusters.append(Cluster(host, port, user, password))
		self.settings.endArray()
		return clusters

	def get_account(self, name):
		self.settings.beginGroup(name)
		user = self.settings.value("user", self.call)
		password = self.settings.value("password", None)
		self.settings.endGroup()
		return Account(user, password)

	def is_empty(self):
		return len(self.settings.allKeys()) == 0

	def write_default_values(self):
		self.call = _callinfo.Call(DEFAULT_CALL)
		self.locator = _grid.Locator(DEFAULT_LOCATOR)
		self.clusters.append(Cluster("arcluster.reversebeacon.net", 7000, str(self.call), None))
		self.hamqth = Account(DEFAULT_CALL, "superSecret")
		self.qrz = Account(DEFAULT_CALL, "superSecret")

		self.settings.setValue("call", str(self.call))
		self.settings.setValue("locator", str(self.locator))
		self.settings.beginWriteArray("clusters")
		for i, cluster in enumerate(self.clusters):
			self.settings.setArrayIndex(i)
			self.settings.setValue("host", cluster.host)
			self.settings.setValue("port", cluster.port)
			self.settings.setValue("user", cluster.user)
			if cluster.password:
				self.settings.setValue("password", cluster.password)
		self.settings.endArray()
		self.settings.beginGroup("hamqth")
		self.settings.setValue("user", self.hamqth.user)
		if self.hamqth.password:
			self.settings.setValue("password", self.hamqth.password)
		self.settings.endGroup()
		self.settings.beginGroup("qrz")
		self.settings.setValue("user", self.qrz.user)
		if self.qrz.password:
			self.settings.setValue("password", self.qrz.password)
		self.settings.endGroup()
		self.settings.sync()

def load_config():
	make_config_dir()
	config = Config()
	if not os.path.isfile(config.filename):
		config.write_default_values()
	return config

def main(args):
	config = load_config()
	print str(config)

if __name__ == "__main__": main(sys.argv)
