#!/usr/bin/python
# -*- coding: utf-8 -*-

import xml.dom.minidom as minidom

class XMLDataElement:
	def __init__(self, dom_element):
		self.dom_element = dom_element

	@staticmethod
	def from_string(s):
		return XMLDataElement(minidom.parseString(unicode(s).encode("utf-8")))

	def __getattr__(self, name):
		if name.startswith("__") and name.endswith("__"): raise AttributeError(name)
		return self[name]

	def __getitem__(self, key):
		if not self.dom_element: return None
		child_element = self._get_single_element_by_name(self.dom_element, key)
		if not child_element: return None
		text_nodes = []
		other_nodes = []
		for node in child_element.childNodes:
			if node.nodeType == node.TEXT_NODE:
				text_nodes.append(node.data)
			else:
				other_nodes.append(node)
		if len(other_nodes) > 0:
			return XMLDataElement(child_element)
		return "".join(text_nodes)

	def __str__(self):
		return self.dom_element.toxml()

	def _get_single_element_by_name(self, parent, element_name):
		elements = parent.getElementsByTagName(element_name)
		if len(elements) == 0:
			return None
		return elements[0]

