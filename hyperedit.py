#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys

# Import Qt modules
import PySide
from PySide import QtGui
from PySide.QtCore import *
from PySide.QtGui import *

from Petter.guihelper import invoke_in_main_thread, exception_handler, PMainWindow

from data_buffer import *
from find_and_replace import FindAndReplace

# Used for saving settings (e.g. in the registry on Windows)
company_name = 'Petter Strandmark'
software_name = 'HyperEdit'
__version__ = '4.0 alpha'

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

		self.cursor_line   = 0
		self.cursor_column = 0

		self.selection_start = -1
		self.selection_end = -1

		self.cursor_color = QColor(255,0,0)
		self.text_color   = QColor(0,0,0)
		self.cursor_background_brush    = QBrush(QColor(255,255,1))
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
		return int(screen_height / self.line_height)

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
			self.data_line = max(0, self.cursor_line - self.number_of_lines_on_screen() / 2)

		self.update()

	def set_selection(self, start, end):
		self.selection_start = start
		self.selection_end = end
		self.update()

	def get_cursor_position(self):
		return self.cursor_line * self.line_width + self.cursor_column


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
					byte = view[self.line_width * l + i]
					num = ord(byte)
					if num >= 32:
						text_string = byte
					byte_string = '%02X' % num

					if i == self.cursor_column and line == self.cursor_line:
						painter.setPen(self.cursor_color)
						painter.setBackgroundMode(Qt.OpaqueMode)
						painter.setBackground(self.cursor_background_brush)
					elif self.selection_start <= global_offset and \
					     global_offset < self.selection_end:
						painter.setBackground(self.selection_background_brush)
						painter.setBackgroundMode(Qt.OpaqueMode)
						byte_string += ' '

					byte_string = byte_string
					byte_point = QPoint(180 + 25*i, (l + 1) * self.line_height)
					painter.drawText(byte_point, byte_string)
					text_point = QPoint(600 + self.character_width*i, (l + 1) * self.line_height)
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
				self.data_line = min(self.number_of_rows(), self.data_line)
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

	def keyPressEvent(self, event):
		if not self.data_buffer:
			return

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

			if line >= 0 and col >= 0:
				cursor_pos = self.cursor_line * self.line_width + self.cursor_column
				click_pos  = line * self.line_width + col
				print cursor_pos, click_pos
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

	def wheelEvent(self, event):
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

		self.find_and_replace = None

	def closeEvent(self, event):
		if self.find_and_replace:
			self.find_and_replace.close()
		PMainWindow.closeEvent(self, event)

	def report_error(self, error, title="Error"):
		 QtGui.QMessageBox.critical(self, title, error)

	@exception_handler
	def resizeEvent(self, event):
		PMainWindow.resizeEvent(self, event)

	def open_file(self, file_name):
		self.ui.view.open(FileBuffer(file_name))

		try:
			self.ui.fileScrollBar.setMinimum(0)
			self.ui.fileScrollBar.setMaximum(max(0, self.ui.view.number_of_rows() - 10))
			self.ui.fileScrollBar.setPageStep(self.ui.view.number_of_lines_on_screen())
			self.ui.fileScrollBar.setEnabled(True)
		except OverflowError:
			# File is so large we cannot use the scroll bar.
			self.ui.fileScrollBar.setEnabled(False)

		self.ui.view.repaint()

		self.statusBar().showMessage('File size: {0}'.format(self.ui.view.data_buffer.length()))

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
	def on_actionFind_Replace_triggered(self):
		if not self.find_and_replace:
			self.find_and_replace = FindAndReplace(self, company_name, software_name)
		self.find_and_replace.set_view(self.ui.view)
		self.find_and_replace.show()

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