#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Petter Strandmark 2013.

import os
import sys

# Import Qt modules
import PySide
from PySide import QtGui
from PySide.QtCore import *
from PySide.QtGui import *

try:
	import win32com.shell.shell as pywin32_shell
except ImportError:
	pywin32_shell = None

from Petter.guihelper import invoke_in_main_thread, exception_handler, PMainWindow

from modules.data_buffer import *
from modules.data_types import DataTypes
from modules.drives import DriveDialog
from modules.find_and_replace import FindAndReplace

# Used for saving settings (e.g. in the registry on Windows)
company_name = 'Petter Strandmark'
software_name = 'HyperEdit'
__version__ = '4.0 alpha'

class HexView(QtGui.QWidget):
	HEX_LEFT = object()
	HEX_RIGHT = object()
	TEXT = object()

	def __init__(self, parent=None, main_window=None):
		super(HexView, self).__init__(parent)
		self.main_window = main_window

		self.line_height = 14.0

		self.font = QFont("DejaVu Sans Mono, Courier, Monospace", 10)
		self.character_width = 10
		self.data_buffer = None
		self.line_width = 16
		self.data_line = 0

		self.cursor_line   = 0
		self.cursor_column = 0
		self.cursor_data_view = None
		self.cursor_hexmode = self.TEXT

		self.selection_start = -1
		self.selection_end = -1

		window_color = self.palette().window().color()
		cursor_disabled_color = QColor()
		cursor_disabled_color.setRedF(window_color.redF()     - 0.1)
		cursor_disabled_color.setGreenF(window_color.greenF() - 0.1)
		cursor_disabled_color.setBlueF(window_color.blueF()   - 0.1)

		self.cursor_color = QColor(255,0,0)
		self.text_color   = QColor(0,0,0)
		self.cursor_background_brush          = QBrush(QColor(255,255,1))
		self.cursor_disabled_background_brush = QBrush(cursor_disabled_color)
		self.selection_background_brush = QBrush(QColor(180,255,180))

		# Accept key strokes.
		self.setFocusPolicy(Qt.WheelFocus)

		# Accept drops.
		self.setAcceptDrops(True)

		# How to report errors.
		#invoke_in_main_thread(self.main_window.report_error, "PetterS", "Title")

	def clear_selection(self):
		self.selection_start = -1
		self.selection_end   = -1
		self.update()

	def open(self, data_buffer):
		self.data_buffer = data_buffer
		if self.data_buffer.length() == 0:
			self.data_buffer = None
			raise RuntimeError('File is empty.')
		# Is the cursor outside the file?
		if self.cursor_line * self.line_width + self.cursor_column >= self.data_buffer.length():
			self.set_cursor_position(self.data_buffer.length() - 1)

		self.update()

	def number_of_lines_on_screen(self):
		screen_height = self.height()
		return int(screen_height // self.line_height)

	def number_of_rows(self):
		num_rows = self.data_buffer.length() // self.line_width
		if self.data_buffer.length() % self.line_width > 0:
			num_rows += 1
		return num_rows

	def set_line(self, line_number):
		self.data_line = line_number
		self.update()

	def set_cursor_position(self, pos):
		self.cursor_line   = pos // self.line_width
		self.cursor_column = pos %  self.line_width

		# Is the cursor visible?
		if self.is_cursor_visible():
			# If the cursor is visible, the data line should not
			# be altered.
			pass
		else:
			# If the cursor is not visible, let it end up in the
			# middle of the screen.
			self.data_line = max(0, self.cursor_line - self.number_of_lines_on_screen() // 2)

		self.main_window.update_line(self.data_line)
		self.update()

	def set_selection(self, start, end):
		self.selection_start = start
		self.selection_end = end
		self.update()

	def get_cursor_position(self):
		return self.cursor_line * self.line_width + self.cursor_column

	def data_at_position(self, position, length = 10):
		view, length = self.data_buffer.read(position, length)
		return view

	def bytes_to_string(self, byte_data):
		output_string = ''
		for i in range(len(byte_data)):
			if byte_data[i] >= 32:
				try:
					# TODO: allow user to change decoder.
					output_string += byte_data[i:i+1].decode('cp1252')
				except:
					output_string += byte_data[i:i+1].decode('cp850')
			else:
				output_string += '.'
		return output_string

	def switch_view(self):
		if self.cursor_hexmode == self.TEXT:
			self.cursor_hexmode = self.HEX_LEFT
		else:
			self.cursor_hexmode = self.TEXT
		self.update()

	def write_byte_string(self, byte_string):
		if len(byte_string) == 0:
			return
		if self.data_buffer.is_readonly():
			return

		num_rows = self.number_of_lines_on_screen()
		view, length = self.data_buffer.read(self.line_width * self.data_line,
		                                     self.line_width * num_rows)
		view_pos = ((self.cursor_line - self.data_line) * self.line_width
			           + self.cursor_column)
		for b in byte_string:
			try:
				view[view_pos] = b
				self.data_buffer.set_modified()
			except:
				# We might be outside the file. This is not an error.
				# Just ignore these bytes.
				pass
			view_pos += 1

		self.update()

# PRIVATE METHODS

	def dragEnterEvent(self, e):
		if e.mimeData().hasUrls():
			e.accept()
		else:
			e.ignore()

	def dropEvent(self, e):
		for url in e.mimeData().urls():
			invoke_in_main_thread(self.main_window.open_file, url.toLocalFile())
			return

	def paintEvent(self, event):
		try:
			return self.paintEvent_main(event)
		except Exception as err:
			print("PAINT EVENT EXCEPTION")
			print("---------------------")
			import traceback
			for tb in traceback.extract_tb(sys.exc_info()[2]):
				# Add info to error string
				file_name = os.path.split(tb[0])[1]
				line = str(tb[1])
				print(file_name, "line", line)
			print(str(err))
			print("---------------------")

	def paintEvent_main(self, event):
		painter = QtGui.QPainter(self)
		painter.setRenderHint(QtGui.QPainter.Antialiasing)
		painter.setFont(self.font)

		if self.data_buffer:
			# Number of lines that fit on screen.
			num_rows = self.number_of_lines_on_screen()
			view, length = self.data_buffer.read(self.line_width * self.data_line,
			                                     self.line_width * num_rows)

			# Number of lines that are needed.
			num_rows = length // self.line_width
			if length % self.line_width > 0:
				num_rows += 1

			for l in range(num_rows):
				line = self.data_line + l
				position_string = '0x%016X' % (self.line_width * line)
				painter.drawText(QPoint(5, (l + 1) * self.line_height), position_string)

				global_offset = line * self.line_width
				for i in range(min(self.line_width, length - self.line_width * l)):
					text_string = '.'
					position = self.line_width * l + i
					num  = view[position]
					byte_string = '%02X' % num
					byte = view[position:position + 1].tobytes()
					text_string = self.bytes_to_string(byte)

					selected = False
					if i == self.cursor_column and line == self.cursor_line:
						# We are at the data cursor.
						selected = True
					elif self.selection_start <= global_offset and \
					     global_offset < self.selection_end:
						painter.setBackground(self.selection_background_brush)
						painter.setBackgroundMode(Qt.OpaqueMode)
						byte_string += ' '

					byte_point = QPoint(180 + 25*i, (l + 1) * self.line_height)
					if selected and self.cursor_hexmode == self.HEX_LEFT:
						painter.setBackground(self.cursor_background_brush)
						painter.setBackgroundMode(Qt.OpaqueMode)
						painter.setPen(self.cursor_color)
					elif selected and self.cursor_hexmode == self.TEXT:
						painter.setBackground(self.cursor_disabled_background_brush)
						painter.setBackgroundMode(Qt.OpaqueMode)
						painter.setPen(self.cursor_color)
					painter.drawText(byte_point, byte_string[0])

					byte_point = QPoint(180 + 25*i + 8, (l + 1) * self.line_height)
					if selected and self.cursor_hexmode == self.HEX_RIGHT:
						painter.setBackground(self.cursor_background_brush)
						painter.setBackgroundMode(Qt.OpaqueMode)
						painter.setPen(self.cursor_color)
					elif selected and self.cursor_hexmode == self.TEXT:
						painter.setBackground(self.cursor_disabled_background_brush)
						painter.setBackgroundMode(Qt.OpaqueMode)
						painter.setPen(self.cursor_color)
					elif selected:
						painter.setBackgroundMode(Qt.TransparentMode)
						painter.setPen(self.text_color)

					painter.drawText(byte_point, byte_string[1])

					text_point = QPoint(600 + self.character_width*i, (l + 1) * self.line_height)
					if selected and self.cursor_hexmode == self.TEXT:
						painter.setBackground(self.cursor_background_brush)
						painter.setBackgroundMode(Qt.OpaqueMode)
						painter.setPen(self.cursor_color)
					elif selected:
						painter.setBackground(self.cursor_disabled_background_brush)
						painter.setBackgroundMode(Qt.OpaqueMode)
						painter.setPen(self.cursor_color)
					painter.drawText(text_point, text_string)

					painter.setPen(self.text_color)
					painter.setBackgroundMode(Qt.TransparentMode)

					global_offset += 1

	def is_cursor_visible(self):
		if self.cursor_line >= self.data_line and \
		   self.cursor_line <  self.data_line + self.number_of_lines_on_screen():
			cursor_visible = True
		else:
			cursor_visible = False
		return cursor_visible

	def scroll_to_cursor(self):
		# Is the cursor too far down?
		if self.cursor_line >= self.data_line + self.number_of_lines_on_screen():
			# Move to the cursor.
			self.data_line = self.cursor_line - self.number_of_lines_on_screen() + 1

		# Is the cursor too far up?
		elif self.cursor_line < self.data_line:
			# Move to the cursor.
			self.data_line = self.cursor_line

	def move_cursor_up(self):
		self.cursor_line = max(0, self.cursor_line - 1)
		self.scroll_to_cursor()

	def move_cursor_down(self):
		new_pos = self.line_width * self.cursor_line + self.cursor_column
		new_pos += self.line_width

		# Is it possible to move down?
		if new_pos < self.data_buffer.length():
			self.cursor_line += 1

		self.scroll_to_cursor()

	def move_cursor_page_up(self):
		new_pos = self.line_width * self.cursor_line + self.cursor_column
		new_pos -= self.line_width * self.number_of_lines_on_screen()

		# Is it possible to move a whole page down?
		if new_pos >= 0:
			# Is the cursor visible?
			cursor_visible = self.is_cursor_visible()

			# Set the new line of the cursor.
			self.cursor_line -= self.number_of_lines_on_screen()

			# Is the cursor visible?
			if cursor_visible:
				# If the cursor is visible, its position in the screen should not
				# be altered.
				self.data_line -= self.number_of_lines_on_screen()
				self.data_line = max(0, self.data_line)
			else:
				# If the cursor is invisible, let it end up in the middle of
				# the screen.
				self.data_line = max(0, self.cursor_line - self.number_of_lines_on_screen() // 2)
		else:
			# If not, then do the equivalent of many 'up' key strokes.
			for i in range(self.number_of_lines_on_screen()):
				self.move_cursor_up()

	def move_cursor_page_down(self):
		new_pos = self.line_width * self.cursor_line + self.cursor_column
		new_pos += self.line_width * self.number_of_lines_on_screen()

		# Is it possible to move a whole page down?
		if new_pos < self.data_buffer.length():
			# Is the cursor visible?
			cursor_visible = self.is_cursor_visible()

			# Set the new line of the cursor.
			self.cursor_line += self.number_of_lines_on_screen()

			# Is the cursor visible?
			if cursor_visible:
				# If the cursor is visible, its position in the screen should not
				# be altered.
				self.data_line += self.number_of_lines_on_screen()
				self.data_line = min(self.number_of_rows(), self.data_line)
			else:
				# If the cursor is invisible, let it end up in the middle of
				# the screen.
				self.data_line = max(0, self.cursor_line - self.number_of_lines_on_screen() // 2)
		else:
			# If not, then do the equivalent of many 'down' key strokes.
			for i in range(self.number_of_lines_on_screen()):
				self.move_cursor_down()

	def move_cursor_left(self):
		if self.cursor_column == 0:
			if self.cursor_line > 0:
				self.cursor_line -= 1
				self.cursor_column = self.line_width - 1
				self.scroll_to_cursor()
		else:
			self.cursor_column = self.cursor_column - 1

	def move_cursor_right(self):
		pos = self.line_width * self.cursor_line + self.cursor_column
		pos += 1
		if self.cursor_column < self.line_width - 1 and pos < self.data_buffer.length():
			self.cursor_column += 1
		elif pos < self.data_buffer.length():
			self.cursor_column = 0
			self.cursor_line += 1
			self.scroll_to_cursor()

	@exception_handler
	def keyPressEvent(self, event):
		if not self.data_buffer:
			return

		key = event.key()

		if key == Qt.Key_Up:
			self.move_cursor_up()
		elif key == Qt.Key_Down:
			self.move_cursor_down()
		elif key == Qt.Key_Left or key == Qt.Key_Backspace:
			if self.cursor_hexmode == self.TEXT:
				self.move_cursor_left()
			elif self.cursor_hexmode == self.HEX_RIGHT:
				self.cursor_hexmode = self.HEX_LEFT
			elif self.cursor_hexmode == self.HEX_LEFT:
				self.move_cursor_left()
				self.cursor_hexmode = self.HEX_RIGHT
		elif key == Qt.Key_Right:
			if self.cursor_hexmode == self.TEXT:
				self.move_cursor_right()
			elif self.cursor_hexmode == self.HEX_LEFT:
				self.cursor_hexmode = self.HEX_RIGHT
			elif self.cursor_hexmode == self.HEX_RIGHT:
				self.move_cursor_right()
				self.cursor_hexmode = self.HEX_LEFT
		elif key == Qt.Key_PageDown:
			self.move_cursor_page_down()
		elif key == Qt.Key_PageUp:
			self.move_cursor_page_up()
		elif len(event.text()) > 0:

			if self.data_buffer.is_readonly():
				return

			num_rows = self.number_of_lines_on_screen()
			view, length = self.data_buffer.read(self.line_width * self.data_line,
			                                     self.line_width * num_rows)

			if self.cursor_hexmode == self.TEXT:
				# TODO: Allow other encodings.
				byte_string = event.text().encode('utf-8')
				for b in byte_string:
					view_pos = ((self.cursor_line - self.data_line) * self.line_width 
					           + self.cursor_column)
					view[view_pos] = b
					self.move_cursor_right()
			else:
				try:
					input_digit = int(event.text(), 16)
					view_pos = ((self.cursor_line - self.data_line) * self.line_width 
					           + self.cursor_column)
					if self.cursor_hexmode == self.HEX_LEFT:
						new_byte = 16 * input_digit + (view[view_pos] & 0x0F)
						view[view_pos] = new_byte
						self.cursor_hexmode = self.HEX_RIGHT
					elif self.cursor_hexmode == self.HEX_RIGHT:
						new_byte = (view[view_pos] & 0xF0) + input_digit
						view[view_pos] = new_byte
						self.cursor_hexmode = self.HEX_LEFT
						self.move_cursor_right()
				except ValueError:
					# The user may have entered an invalid hex digit.
					# Not an error.
					return

			# Mark the buffer modified since last read.
			self.data_buffer.set_modified()
		else:
			event.ignore()
			return

		self.main_window.update_line(self.data_line)
		self.update()

	def xy_to_linecol(self, x, y):
		new_line = None
		new_col  = None

		for line in range(self.number_of_lines_on_screen()):
			if line * self.line_height <= y and y <= (line + 1) * self.line_height:
				new_line = line
				break

		for col in range(self.line_width):
			if 180 + 25*col <= x and x <= 180 + 25*col + 20:
				new_col = col
				break
			if 600 + col * self.character_width <= x and x <= 600 + (col + 1) * self.character_width:
				new_col = col
				break

		if new_line is not None and new_col is not None:
			new_line = self.data_line + new_line
			# Is the new row and column valid?
			new_pos = new_line * self.line_width + new_col
			if new_pos >= self.data_buffer.length():
				new_line = None
				new_col  = None

		return new_line, new_col

	@exception_handler
	def mousePressEvent(self, event):
		if not self.data_buffer:
			return

		button = event.button()
		x = event.x()
		y = event.y()
		if button == Qt.LeftButton:
			line, col = self.xy_to_linecol(x, y)
			if line is not None and col is not None:
				self.cursor_line   = line
				self.cursor_column = col
		elif button == Qt.RightButton:
			line, col = self.xy_to_linecol(x, y)

			if line is not None and col is not None:
				cursor_pos = self.cursor_line * self.line_width + self.cursor_column
				click_pos  = line * self.line_width + col

				if click_pos > cursor_pos:
					self.selection_start = cursor_pos
					self.selection_end   = click_pos + 1
				elif click_pos < cursor_pos:
					self.selection_start = click_pos
					self.selection_end   = cursor_pos + 1
				else:
					self.selection_start = -1
					self.selection_end   = -1
		else:
			return

		self.main_window.update_line(self.data_line)
		self.update()

	@exception_handler
	def wheelEvent(self, event):
		if not self.data_buffer:
			return

		lines_delta = - int(0.3 * event.delta() / self.line_height)
		if lines_delta <= 0:
			self.data_line = max(self.data_line + lines_delta, 0)
		else:
			self.data_line = min(self.data_line + lines_delta,
			                     self.number_of_rows())

		self.main_window.update_line(self.data_line)
		self.update()
#
# MAIN WINDOW
#
class Main(PMainWindow):
	def __init__(self):
		PMainWindow.__init__(self, "hexeditor.ui", company_name, software_name)
		self.setWindowTitle("HyperEdit")

		self.ui.view = HexView(self.ui.centralwidget, self)
		self.ui.horizontalLayout.insertWidget(0,self.ui.view)

		self.ui.fileScrollBar.setEnabled(False)

		self.clipboard = QApplication.clipboard()

		self.find_and_replace = None
		self.data_types = None

		# Set up status bar
		self.status_bar_position         = QLabel("")
		self.status_bar_position_hex     = QLabel("")
		self.status_bar_position_percent = QLabel("")
		self.status_bar_file_size        = QLabel("")
		self.status_bar_modified         = QLabel("")
		self.statusBar().addPermanentWidget(self.status_bar_modified)
		self.statusBar().addPermanentWidget(self.status_bar_file_size)
		self.statusBar().addPermanentWidget(self.status_bar_position)
		self.statusBar().addPermanentWidget(self.status_bar_position_hex)
		self.statusBar().addPermanentWidget(self.status_bar_position_percent)

		# Set up scoll bar
		self.ui.fileScrollBar.ignore_valueChanged = False

		self.ASADMIN = 'asadmin'
		if pywin32_shell is None or self.ASADMIN in sys.argv:
			self.ui.actionElevate.setEnabled(False)

		if self.ASADMIN in sys.argv:
			self.setWindowTitle("HyperEdit (ADMINISTRATOR)")

	@exception_handler
	def closeEvent(self, event):
		if self.ui.view.data_buffer is not None:
			self.ui.view.data_buffer.flush()

		if self.find_and_replace:
			self.find_and_replace.close()
		if self.data_types:
			self.data_types.close()
		PMainWindow.closeEvent(self, event)

	@exception_handler
	def changeEvent(self, event):
		if event.type() == QEvent.ActivationChange:
			# Another window on the desktop has been
			# activated or deactivated.
			if self.ui.view.data_buffer is not None:
				self.ui.view.data_buffer.flush()
			self.status_bar_modified.setText("")
			event.accept()
		PMainWindow.changeEvent(self, event)

	def report_error(self, error, title="Error"):
		 QtGui.QMessageBox.critical(self, title, error)

	@exception_handler
	def resizeEvent(self, event):
		PMainWindow.resizeEvent(self, event)

	def open_file(self, file_name, is_drive = False):
		if is_drive:
			buffer = DriveBuffer(file_name)
		else:
			buffer = FileBuffer(file_name, readonly=False)
		self.ui.view.open(buffer)

		self.ui.fileScrollBar.setEnabled(True)
		self.ui.actionFind_Replace.setEnabled(True)
		try:
			self.ui.fileScrollBar.setMinimum(0)
			self.ui.fileScrollBar.setMaximum(max(0, self.ui.view.number_of_rows() - 10))
			self.ui.fileScrollBar.setPageStep(self.ui.view.number_of_lines_on_screen())

			self.scrollbar_factor = None
			self.ui.fileScrollBar.setEnabled(True)
		except OverflowError:
			# File is so large we cannot use the scroll bar.
			#self.ui.fileScrollBar.setEnabled(False)

			wanted_size = self.ui.view.number_of_rows() - 10
			self.scrollbar_factor = wanted_size // 1000**3
			self.ui.fileScrollBar.setMaximum(wanted_size // self.scrollbar_factor)
			self.ui.fileScrollBar.setPageStep(self.ui.view.number_of_lines_on_screen() // self.scrollbar_factor)

			self.statusBar().showMessage("Warning: Scrollbar not exact due to Qt limitation.")
			self.ui.fileScrollBar.setEnabled(True)

		# Set the file size in the status bar.
		file_size = self.ui.view.data_buffer.length()
		if file_size < 1024:
			self.status_bar_file_size.setText("File size: {0} bytes".format(file_size))
		elif file_size < 1024**2:
			self.status_bar_file_size.setText("File size: {0} bytes ({1:.2f} kB)"
			                                  .format(file_size, file_size / 1024))
		elif file_size < 1024**3:
			self.status_bar_file_size.setText("File size: {0} bytes ({1:.2f} MB)"
			                                  .format(file_size, file_size / 1024**2))
		else:
			self.status_bar_file_size.setText("File size: {0} bytes ({1:.2f} GB)"
			                                  .format(file_size, file_size / 1024**3))
		# Repaint the hexagonal view.
		self.ui.view.repaint()

	@Slot()
	@exception_handler
	def on_actionOpen_triggered(self):
		default_dir = self.settings.value("default_dir", '')
		filter = "All files (*)"
		(file_name, mask)=QtGui.QFileDialog.getOpenFileName(self,"Choose a file", default_dir, filter)
		if file_name :
			dir, fname = os.path.split(file_name)
			self.settings.setValue("default_dir", dir)
			self.open_file(file_name)

	@Slot()
	@exception_handler
	def on_actionOpen_Drive_triggered(self):
		self.drive_dialog = DriveDialog(self, company_name, software_name)
		self.drive_dialog.set_view(self.ui.view)
		self.drive_dialog.exec_()

	@Slot()
	@exception_handler
	def on_actionAbout_triggered(self):
		QMessageBox.about(self, "About HyperEdit",
			u"""<b>HyperEdit</b> v %s
			<p>Copyright © 2013 Petter Strandmark.
			<p>PySide version %s - Qt version %s""" % (__version__,
			PySide.__version__,  PySide.QtCore.__version__,))
	@Slot()
	@exception_handler
	def on_actionClear_Selection_triggered(self):
		self.ui.view.clear_selection()

	@Slot()
	@exception_handler
	def on_actionSwitch_View_triggered(self):
		self.ui.view.switch_view()

	@Slot()
	@exception_handler
	def on_actionFind_Replace_triggered(self):
		if not self.find_and_replace:
			self.find_and_replace = FindAndReplace(self, company_name, software_name)
		self.find_and_replace.set_view(self.ui.view)
		self.find_and_replace.show()

	@Slot()
	@exception_handler
	def on_actionData_Types_triggered(self):
		if not self.data_types:
			self.data_types = DataTypes(self, company_name, software_name)
		self.data_types.set_view(self.ui.view)
		self.data_types.show()
		self.data_types.update()

	@Slot()
	@exception_handler
	def on_actionElevate_triggered(self):
		if pywin32_shell is not None:
			if self.ASADMIN not in sys.argv:
				script = os.path.abspath(sys.argv[0])
				params = ' '.join(["\"" + script + "\""] + sys.argv[1:] + [self.ASADMIN])
				print("Elevating...")
				pywin32_shell.ShellExecuteEx(lpVerb='runas', lpFile=sys.executable, lpParameters=params, nShow=1)
				self.close()

	@Slot()
	@exception_handler
	def on_actionExit_triggered(self):
		self.close()

	@Slot()
	@exception_handler
	def on_actionCopy_triggered(self):
		length = self.ui.view.selection_end - self.ui.view.selection_start
		data = self.ui.view.data_at_position(self.ui.view.selection_start,
		                                     length)
		byte_data = data[:length].tobytes()
		if self.ui.view.cursor_hexmode == self.ui.view.TEXT:
			string_data = self.ui.view.bytes_to_string(byte_data)
		else:
			string_data = ''.join( ["%02X " %  x for x in byte_data] ).strip()
		self.clipboard.setText(string_data)

	@Slot()
	@exception_handler
	def on_fileScrollBar_valueChanged(self):

		# If we are supposed to ignore this event, return.
		if self.ui.fileScrollBar.ignore_valueChanged:
			self.ui.fileScrollBar.ignore_valueChanged = False
			return

		if self.scrollbar_factor is None:
			# Scroll bar is exact.
			self.ui.view.set_line(self.ui.fileScrollBar.value())
		else:
			# There are too many lines for the scrollbar to show exactly.
			value = self.ui.fileScrollBar.value()
			self.ui.view.set_line(value * self.scrollbar_factor)

	@exception_handler
	def update_line(self, line):

		if self.scrollbar_factor is None:
			# Scroll bar is exact.
			if self.ui.fileScrollBar.value() != line:
				self.ui.fileScrollBar.ignore_valueChanged = True
				self.ui.fileScrollBar.setValue(line)
		else:
			# There are too many lines for the scrollbar to show exactly.
			scrollbar_pos = line // self.scrollbar_factor
			if self.ui.fileScrollBar.value() != scrollbar_pos:
				self.ui.fileScrollBar.ignore_valueChanged = True
				self.ui.fileScrollBar.setValue(scrollbar_pos)

		if self.data_types:
			self.data_types.update()

		if self.ui.view.selection_start >= 0 and \
		   self.ui.view.selection_end >= 0:
			self.ui.actionCopy.setEnabled(True)
		else:
			self.ui.actionCopy.setEnabled(False)

		position = self.ui.view.get_cursor_position()
		file_size = self.ui.view.data_buffer.length()
		self.status_bar_position.setText("{0}".format(position))
		self.status_bar_position_hex.setText("0x{0:x}".format(position))
		self.status_bar_position_percent.setText("{0:.2f}%".format(100 * (position + 1) / file_size))
		if self.ui.view.data_buffer.is_modified():
			self.status_bar_modified.setText("Modified.")
		else:
			self.status_bar_modified.setText("")

def main():
	app = QtGui.QApplication(sys.argv)
	window=Main()
	window.show()

	icon = QtGui.QIcon('images/icon.png')
	app.setWindowIcon(icon)
	window.setWindowIcon(icon)

	sys.exit(app.exec_())

if __name__ == "__main__":
	main()