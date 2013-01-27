
import binascii
from time import sleep

from PySide import QtUiTools
from PySide.QtCore import *
from PySide.QtGui import *

from Petter.guihelper import invoke_in_main_thread, exception_handler

class FindAndReplace(QMainWindow):
	def __init__(self, main_window, company_name, software_name):
		QMainWindow.__init__(self)
		self.setWindowTitle("Find and Replace")
		self.setWindowFlags(Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)

		self.main_window = main_window

		# Set up UI
		loader = QtUiTools.QUiLoader()
		self.ui = loader.load('find_and_replace.ui', None)
		self.setCentralWidget(self.ui)
		QMetaObject.connectSlotsByName(self)

		# Size constraints
		self.setMinimumSize(self.ui.minimumSize())
		self.setMaximumSize(self.ui.maximumSize())

		# Read settings
		self.settings = QSettings(company_name, software_name)
		self.restoreGeometry(self.settings.value("FindAndReplace/geometry"))

		self.view = None

	def set_view(self, view):
		self.view = view

	def showEvent(self, event):
		self.setEnabled(True)
		QMainWindow.showEvent(self, event)

	def closeEvent(self, event):
		self.settings.setValue("FindAndReplace/geometry", self.saveGeometry())
		QMainWindow.closeEvent(self, event)

	def setEnabled(self, enabled):
		self.ui.findButton.setEnabled(enabled)
		self.ui.replaceButton.setEnabled(False)

	@Slot()
	@exception_handler
	def on_findButton_clicked(self):
		self.setEnabled(False)

		progress_ticks = 1000000000
		progress = QProgressDialog("Searching file...", "Cancel", 0, progress_ticks, self.main_window)
		progress.setWindowModality(Qt.WindowModal)
		progress.setWindowTitle("Find and Replace")
		progress.setAutoClose(False)
		progress.setAutoReset(False)
		progress.setMinimumDuration(400)

		step_length = 100 * 1024
		file_length = self.view.data_buffer.length()

		current_pos = self.view.get_cursor_position()
		# If the cursor is in the selection, start at the end of
		# the selection (to find the next match).
		if self.view.selection_start <= current_pos and \
		   current_pos < self.view.selection_end:
			current_pos = self.view.selection_end
			# This may have taken us beyond the file end;
			# if so, start over.
			if current_pos >= file_length:
				current_pos = 0

		start_pos = current_pos
		bytes_searched = 0

		wanted_bytes = None
		if self.ui.stringButton.isChecked():
			encoding = self.ui.encodingEdit.text()
			wanted_bytes = self.ui.searchEdit.text().encode(encoding)
		elif self.ui.hexButton.isChecked():
			hex_string = self.ui.searchEdit.text().encode('utf-8')
			hex_string = hex_string.replace(" ", "")
			wanted_bytes = binascii.unhexlify(hex_string)

		wrapped_around = False
		while(bytes_searched < file_length):
			fraction_complete = min(1.0, float(bytes_searched) / file_length)
			progress.setValue(int(fraction_complete * progress_ticks))
			if progress.wasCanceled():
				break

			view, length = self.view.data_buffer.read(current_pos, step_length)
			# Convert view to bytes for searching.
			bytes = view[:length].tobytes()
			# Search in the bytes.
			found_index = bytes.find(wanted_bytes)
			if found_index >= 0:
				# Set cursor position and selection to the found string.
				self.view.set_cursor_position(current_pos + found_index)
				self.view.set_selection(current_pos + found_index,
				                        current_pos + found_index + len(wanted_bytes))
				break
			else:
				bytes_searched += length
				current_pos += length

			if current_pos >= file_length:
				current_pos = 0
				wrapped_around = True
			if wrapped_around and current_pos >= start_pos + step_length:
				break


		progress.close()
		self.setEnabled(True)
