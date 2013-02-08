
import binascii
import re

from PySide import QtUiTools
from PySide.QtCore import *
from PySide.QtGui import *

from Petter.guihelper import exception_handler

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
		self.ui.encodingEdit.setText(self.settings.value("FindAndReplace/encoding", "utf-8"))
		self.ui.searchEdit.setText(self.settings.value("FindAndReplace/search", ""))

		self.view = None

	def set_view(self, view):
		self.view = view

	def showEvent(self, event):
		self.setEnabled(True)
		QMainWindow.showEvent(self, event)

	def closeEvent(self, event):
		self.settings.setValue("FindAndReplace/geometry", self.saveGeometry())
		self.settings.setValue("FindAndReplace/encoding", self.ui.encodingEdit.text())
		self.settings.setValue("FindAndReplace/search", self.ui.searchEdit.text())
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

		encoding = self.ui.encodingEdit.text()

		wanted_bytes = None
		regex_selected = False
		if self.ui.stringButton.isChecked():
			wanted_bytes = self.ui.searchEdit.text().encode(encoding)
		elif self.ui.hexButton.isChecked():
			hex_string = self.ui.searchEdit.text()
			hex_string = hex_string.replace(" ", "")
			wanted_bytes = binascii.unhexlify(hex_string)
		elif self.ui.regexButton.isChecked():
			regex_selected = True
			regex = re.compile(self.ui.searchEdit.text().encode(encoding))

		wrapped_around = False
		while(bytes_searched < file_length):
			fraction_complete = min(1.0, float(bytes_searched) / file_length)
			progress.setValue(int(fraction_complete * progress_ticks))
			if progress.wasCanceled():
				break

			view, length = self.view.data_buffer.read(current_pos, step_length)
			# Convert view to bytes for searching.
			bytes = view[:length].tobytes()
			if not regex_selected:
				# Search in the bytes.
				found_start = bytes.find(wanted_bytes)
				found_end   = found_start + len(wanted_bytes)
			else:
				# Search in the bytes using regex.
				match = regex.search(bytes)
				if match is None:
					found_start = -1
				else:
					found_start = match.start()
					found_end   = match.end()

			if found_start >= 0:
				# Set cursor position and selection to the found string.
				self.view.set_cursor_position(current_pos + found_start)
				self.view.set_selection(current_pos + found_start,
				                        current_pos + found_end)
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
