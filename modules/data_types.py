# -*- coding: utf-8 -*-
#
# Petter Strandmark 2013.

import binascii
import os
import struct

from PySide import QtUiTools
from PySide.QtCore import *
from PySide.QtGui import *

from Petter.guihelper import exception_handler

class DataTypes(QMainWindow):
	def __init__(self, main_window, company_name, software_name):
		QMainWindow.__init__(self)
		self.setWindowTitle("Data Types")
		self.setWindowFlags(Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)

		self.main_window = main_window

		# Set up UI
		loader = QtUiTools.QUiLoader()
		this_dir = os.path.dirname(__file__)
		self.ui = loader.load(os.path.join(this_dir, 'data_Types.ui'), None)
		self.setCentralWidget(self.ui)
		QMetaObject.connectSlotsByName(self)

		# Size constraints
		self.setMinimumSize(self.ui.minimumSize())
		self.setMaximumSize(self.ui.maximumSize())

		# Read settings
		self.settings = QSettings(company_name, software_name)
		self.restoreGeometry(self.settings.value("DataTypes/geometry"))
		self.view = None

	def set_view(self, view):
		self.view = view

	def get_format_string(self):
		if self.ui.littleEndianCheckBox.isChecked():
			format_string = '<'
		else:
			format_string = '>'

		if self.ui.eightBitRadioButton.isChecked():
			format_string += 'b'
			printf_string = '%d'
		elif self.ui.sixteenBitRadioButton.isChecked():
			format_string += 'h'
			printf_string = '%d'
		elif self.ui.thirtyTwoBitRadioButton.isChecked():
			format_string += 'i'
			printf_string = '%d'
		elif self.ui.sixtyFourBitRadioButton.isChecked():
			format_string += 'q'
			printf_string = '%d'

		if not self.ui.signedCheckBox.isChecked():
			format_string = format_string.upper()

		if self.ui.singleRadioButton.isChecked():
			format_string += 'f'
			printf_string = '%e'
		elif self.ui.doubleRadioButton.isChecked():
			format_string += 'd'
			printf_string = '%e'

		return format_string, printf_string

	def set_hexEdit_bytes(self, bytes):
		text = ''.join( [ "%02X " %  x for x in bytes ] ).strip()
		self.ui.hexEdit.setText(text)

		# If there is text in the hex data field, the change
		# button should be activated.
		if len(text) > 0:
			self.ui.changeButton.setEnabled(True)
		else:
			self.ui.changeButton.setEnabled(False)

	def set_bytes(self, bytes_or_view):
		current_tab = self.ui.tabWidget.currentWidget()

		if current_tab == self.ui.tab_numbers:
			#Get the format string.
			format_string, printf_string = self.get_format_string()
			# Compute how many bytes are needed.
			size_needed = struct.calcsize(format_string)
			# Extract the correct number of bytes if the
			# input is a memoryview.
			if isinstance(bytes_or_view, memoryview):
				bytes_or_view = bytes_or_view[:size_needed].tobytes()

			# Try and parse a number.
			self.ui.numberEdit.setEnabled(True)
			if printf_string == '%d':
				self.ui.signedCheckBox.setEnabled(True)
			else:
				self.ui.signedCheckBox.setEnabled(False)
			self.ui.littleEndianCheckBox.setEnabled(True)

			number = None
			try:
				assert(size_needed == len(bytes_or_view))
				number = struct.unpack(format_string, bytes_or_view)[0]
			except:
				self.ui.numberEdit.setText("n/a")
				self.ui.numberEdit.setEnabled(False)
				self.ui.signedCheckBox.setEnabled(False)
				self.ui.littleEndianCheckBox.setEnabled(False)

			if number is not None:
				self.ui.numberEdit.setText(printf_string % number)
				number_bytes = struct.pack(format_string, number)
				self.set_hexEdit_bytes(number_bytes)

		elif current_tab == self.ui.tab_dates:
			pass


	def update(self):
		if not self.view:
			return
		if not self.view.data_buffer:
			return
		data_view = self.view.data_at_position(self.view.get_cursor_position())
		self.set_bytes(data_view)

	def showEvent(self, event):
		QMainWindow.showEvent(self, event)

	def closeEvent(self, event):
		self.settings.setValue("DataTypes/geometry", self.saveGeometry())
		QMainWindow.closeEvent(self, event)

	@Slot()
	@exception_handler
	def on_hexEdit_textEdited(self):
		# Fires only when the text is edited by the user, not
		# by the program.
		try:
			hex_string = self.ui.hexEdit.text()
			hex_string = hex_string.replace(" ", "")
			bytes = binascii.unhexlify(hex_string)
			# This is a valid hex string. Enable the change button.
			self.ui.changeButton.setEnabled(True)
		except:
			bytes = ''
			# For invalid hex strings, the change button should be disabled.
			self.ui.changeButton.setEnabled(False)
		self.set_bytes(bytes)

	@Slot()
	@exception_handler
	def on_numberEdit_textEdited(self):
		# Fires only when the text is edited by the user, not
		# by the program.
		number_string = self.ui.numberEdit.text().encode('utf-8')
		format_string, printf_string = self.get_format_string()
		try:
			number = None
			if printf_string == '%d':
				number = int(number_string)
			elif printf_string == '%e':
				number = float(number_string)
			bytes = struct.pack(format_string, number)
		except ValueError:
			bytes = ''
		except struct.error:
			bytes = ''
		self.set_hexEdit_bytes(bytes)


	@Slot()
	@exception_handler
	def on_changeButton_clicked(self):
		# Copy the hex data from hexEdit to the editor in the main
		# window.

		# First, get the hex data.
		try:
			hex_string = self.ui.hexEdit.text()
			hex_string = hex_string.replace(" ", "")
			byte_string = binascii.unhexlify(hex_string)
		except:
			byte_string = b''

		self.view.write_byte_string(byte_string)

	@Slot()
	@exception_handler
	def on_tabWidget_currentChanged(self):
		self.update()

	@Slot()
	@exception_handler
	def on_eightBitRadioButton_clicked(self):
		self.update()

	@Slot()
	@exception_handler
	def on_sixteenBitRadioButton_clicked(self):
		self.update()

	@Slot()
	@exception_handler
	def on_thirtyTwoBitRadioButton_clicked(self):
		self.update()

	@Slot()
	@exception_handler
	def on_sixtyFourBitRadioButton_clicked(self):
		self.update()

	@Slot()
	@exception_handler
	def on_signedCheckBox_clicked(self):
		if len(self.ui.hexEdit.text()) == 0:
			self.update()
		else:
			self.on_hexEdit_textEdited()

	@Slot()
	@exception_handler
	def on_littleEndianCheckBox_clicked(self):
		self.on_hexEdit_textEdited()

	@Slot()
	@exception_handler
	def on_singleRadioButton_clicked(self):
		self.update()

	@Slot()
	@exception_handler
	def on_doubleRadioButton_clicked(self):
		self.update()
