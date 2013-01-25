#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys

# Import Qt modules
from PySide import QtGui
from PySide.QtCore import *
from PySide.QtGui import *

from Petter.guihelper import invoke_in_main_thread, exception_handler, PMainWindow

from data_buffer import *

# Used for saving settings (e.g. in the registry on Windows)
company_name = 'Petter Strandmark'
software_name = 'HyperEdit'

class HexView(QtGui.QWidget):
	def __init__(self, parent=None, main_window=None):
		super(HexView, self).__init__(parent)
		self.main_window = main_window

		self.line_height = 14.0

		self.font = QFont("DejaVu Sans Mono, Courier, Monospace", 10)
		self.character_width = 10
		self.data_buffer = None
		self.line_width = 16
		self.data_line = 0

		self.cursor_line   = 1
		self.cursor_column = 3

		self.cursor_color = QColor(255,0,0)
		self.text_color   = QColor(0,0,0)
		self.cursor_background_brush = QBrush(QColor(255,255,1))

		# Accept key strokes.
		self.setFocusPolicy(Qt.WheelFocus)

		# Accept drops.
		self.setAcceptDrops(True)

		# How to report errors.
		#invoke_in_main_thread(self.main_window.report_error, "PetterS", "Title")

	def open(self, data_buffer):
		self.data_buffer = data_buffer

	def number_of_lines_on_screen(self):
		screen_height = self.height()
		return int(screen_height / self.line_height)

	def number_of_lines(self):
		num_lines = self.data_buffer.length() // self.line_width
		if self.data_buffer.length() % self.line_width > 0:
			num_lines += 1
		return num_lines

	def set_line(self, line_number):
		self.data_line = line_number
		self.repaint()

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
			self.data_line = max(0, self.cursor_line - self.number_of_lines_on_screen() / 2)

		self.repaint()


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
		painter = QtGui.QPainter(self)
		painter.setRenderHint(QtGui.QPainter.Antialiasing)
		painter.setFont(self.font)
		painter.setBackground(self.cursor_background_brush)

		if self.data_buffer:
			# Number of lines that fit on screen.
			num_lines = self.number_of_lines_on_screen()
			view, length = self.data_buffer.read(self.line_width * self.data_line,
			                                     self.line_width * num_lines)

			# Number of lines that are needed.
			num_lines = length // self.line_width
			if length % self.line_width > 0:
				num_lines += 1

			for l in range(num_lines):
				line = self.data_line + l
				position_string = '0x%016X' % (self.line_width * line)
				painter.drawText(QPoint(5, (l + 1) * self.line_height), position_string)

				for i in range(min(self.line_width, length - self.line_width * l)):
					text_string = '.'
					byte = view[self.line_width * l + i]
					num = ord(byte)
					if num >= 32:
						text_string = byte
					byte_string = '%02X' % num

					if i == self.cursor_column and line == self.cursor_line:
						painter.setPen(self.cursor_color)
						painter.setBackgroundMode(Qt.OpaqueMode)

					byte_string = byte_string
					byte_point = QPoint(180 + 25*i, (l + 1) * self.line_height)
					painter.drawText(byte_point, byte_string)
					text_point = QPoint(600 + self.character_width*i, (l + 1) * self.line_height)
					painter.drawText(text_point, text_string)

					painter.setPen(self.text_color)
					painter.setBackgroundMode(Qt.TransparentMode)

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
				self.data_line = max(0, self.cursor_line - self.number_of_lines_on_screen() / 2)
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
				self.data_line = min(self.number_of_lines(), self.data_line)
			else:
				# If the cursor is invisible, let it end up in the middle of
				# the screen.
				self.data_line = max(0, self.cursor_line - self.number_of_lines_on_screen() / 2)
		else:
			# If not, then do the equivalent of many 'down' key strokes.
			for i in range(self.number_of_lines_on_screen()):
				self.move_cursor_down()

	def move_cursor_left(self):
		self.cursor_column = max(0, self.cursor_column - 1)

	def move_cursor_right(self):
		pos = self.line_width * self.cursor_line + self.cursor_column
		pos += 1
		if self.cursor_column < self.line_width - 1 and pos < self.data_buffer.length():
			self.cursor_column += 1
			self.repaint()

	def keyPressEvent(self, event):
		key = event.key()
		if key == Qt.Key_Up:
			self.move_cursor_up()
		elif key == Qt.Key_Down:
			self.move_cursor_down()
		elif key == Qt.Key_Left:
			self.move_cursor_left()
		elif key == Qt.Key_Right:
			self.move_cursor_right()
		elif key == Qt.Key_PageDown:
			self.move_cursor_page_down()
		elif key == Qt.Key_PageUp:
			self.move_cursor_page_up()
		else:
			return

		invoke_in_main_thread(self.main_window.update_line, self.data_line)
		self.repaint()

	def xy_to_rowcol(self, x, y):
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

		if new_line and new_col:
			new_line = self.data_line + new_line
			# Is the new row and column valid?
			new_pos = new_line * self.line_width + new_col
			if new_pos >= self.data_buffer.length():
				new_line = None
				new_col  = None

		return new_line, new_col

	def mousePressEvent(self, event):
		button = event.button()
		x = event.x()
		y = event.y()
		if button == Qt.LeftButton:
			line, col = self.xy_to_rowcol(x, y)

			if line >= 0 and col >= 0:
				self.cursor_line   = line
				self.cursor_column = col
		else:
			return

		invoke_in_main_thread(self.main_window.update_line, self.data_line)
		self.repaint()
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

	def report_error(self, error, title="Error"):
		 QtGui.QMessageBox.critical(self, title, error)

	@exception_handler
	def resizeEvent(self, event):
		PMainWindow.resizeEvent(self, event)

	def disableUI(self, disabled) :
		pass


	def open_file(self, file_name):
		self.ui.view.open(FileBuffer(file_name))

		try:
			self.ui.fileScrollBar.setMinimum(0)
			self.ui.fileScrollBar.setMaximum(max(0, self.ui.view.number_of_lines() - 10))
			self.ui.fileScrollBar.setPageStep(self.ui.view.number_of_lines_on_screen())
			self.ui.fileScrollBar.setEnabled(True)
		except OverflowError:
			# File is so large we cannot use the scroll bar.
			self.ui.fileScrollBar.setEnabled(False)

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
	def on_fileScrollBar_valueChanged(self):
		self.ui.view.set_line(self.ui.fileScrollBar.value())

	def update_line(self, line):
		if self.ui.fileScrollBar.isEnabled():
			if self.ui.fileScrollBar.value() != line:
				self.ui.fileScrollBar.setValue(line)

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