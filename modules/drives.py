# -*- coding: utf-8 -*-
#
# Petter Strandmark 2013.

import os

try:
	import pywintypes
	import win32file
	import win32api
except:
	win32api  = None
	win32file = None


from PySide import QtGui, QtUiTools
from PySide.QtCore import *
from PySide.QtGui import *

from Petter.guihelper import exception_handler, invoke_in_main_thread


class DriveDialog(QDialog):
	def __init__(self, main_window, company_name, software_name):
		QDialog.__init__(self)
		self.setWindowTitle("Open Drive")
		self.setWindowFlags(Qt.CustomizeWindowHint |
		                    Qt.WindowTitleHint |
		                    Qt.WindowCloseButtonHint)

		self.main_window = main_window

		# Set up UI
		loader = QtUiTools.QUiLoader()
		this_dir = os.path.dirname(__file__)
		self.ui = loader.load(os.path.join(this_dir, 'drives.ui'), self)
		layout = QVBoxLayout()
		layout.addWidget(self.ui)
		self.setLayout(layout)

		QMetaObject.connectSlotsByName(self)

		# Size constraints
		self.setMinimumSize(self.ui.minimumSize())
		self.setMaximumSize(self.ui.maximumSize())

		# Read settings
		self.settings = QSettings(company_name, software_name)
		self.restoreGeometry(self.settings.value("Drives/geometry"))
		self.ui.driveTree.setColumnCount(2)
		self.ui.driveTree.setHeaderLabels(['Drive', 'Description'])
		main_window.get_tree_header_width(self.ui.driveTree, 'drives')

		self.view = None

		# Populate drive list
		if win32file is not None:
			drives = win32api.GetLogicalDriveStrings()
			drive_list = drives.strip('\x00').split('\x00')
			for drive in drive_list:
				try:
					space = win32file.GetDiskFreeSpace(drive)
					size = space[0] * space[1] * space[3]
					newItem = QTreeWidgetItem([drive, "{0:.2f} GB".format(size / 1024**3)])
				except pywintypes.error as err:
					newItem = QTreeWidgetItem([drive, err.strerror])
				newItem.drive = drive
				self.ui.driveTree.addTopLevelItem(newItem)
		else:
			QtGui.QMessageBox.critical(self, "pywin32 not found",
"""Pywin32 is required to be able to use this feature.

Install it (if you are using Windows) and try again.""")
			# If we call close directly, the dialog will remain open.
			invoke_in_main_thread(self.close)

	def set_view(self, view):
		self.view = view

	def closeEvent(self, event):
		self.settings.setValue("Drives/geometry", self.saveGeometry())
		self.main_window.set_tree_header_width(self.ui.driveTree, 'drives')
		QDialog.closeEvent(self, event)

	@Slot()
	@exception_handler
	def on_driveTree_currentItemChanged(self):
		item = self.ui.driveTree.currentItem()
		enable = item is not None
		self.ui.openButton.setEnabled(enable)

	@Slot()
	@exception_handler
	def on_driveTree_itemDoubleClicked(self):
		self.ui.openButton.click()

	@Slot()
	@exception_handler
	def on_openButton_clicked(self):
		item = self.ui.driveTree.currentItem()
		self.main_window.open_file(item.drive, True)
		self.close()
