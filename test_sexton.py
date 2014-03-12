#!/usr/bin/python3
# -*- coding: utf-8 -*-

import unittest
import sys

from PySide import QtCore, QtGui

import sexton
from modules.data_buffer import TestBuffer

# Create an application without GUI support. This allows
# tests to be run without an X server.
app = QtGui.QApplication(sys.argv, QtGui.QApplication.Tty)

class TestHexView(unittest.TestCase):

	def setUp(self):
		# This is run before each test_* method.
		self.view = sexton.HexView(None, None, False)

	def test_open_file(self):
		data_buffer = TestBuffer(10000)
		self.view.open(data_buffer)

	def test_write(self):
		data_buffer = TestBuffer(10000)
		self.view.open(data_buffer)
		self.view.set_cursor_position(0)
		self.view.write_byte_string(b'Petter')

		#Open a new file
		self.view.open(TestBuffer(1000))

		# Check contents of first buffer.
		self.assertEqual(data_buffer.buffer[0], ord(b'P'))
		self.assertEqual(data_buffer.buffer[1], ord(b'e'))
		self.assertEqual(data_buffer.buffer[2], ord(b't'))
		self.assertEqual(data_buffer.buffer[3], ord(b't'))
		self.assertEqual(data_buffer.buffer[4], ord(b'e'))
		self.assertEqual(data_buffer.buffer[5], ord(b'r'))

if __name__ == '__main__':
	unittest.main(verbosity=2)
