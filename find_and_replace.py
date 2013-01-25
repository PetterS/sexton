
from PySide import QtUiTools
from PySide.QtCore import *
from PySide.QtGui import *

class FindAndReplace(QMainWindow):
	def __init__(self, company_name, software_name):
		QMainWindow.__init__(self)
		self.setWindowTitle("Find and Replace")
		self.setWindowFlags(Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)

		# Set up UI
		loader = QtUiTools.QUiLoader()
		self.ui = loader.load('find_and_replace.ui', None)
		self.setCentralWidget(self.ui)
		QMetaObject.connectSlotsByName(self)

		# Read settings
		self.settings = QSettings(company_name, software_name)
		self.restoreGeometry(self.settings.value("FindAndReplace/geometry"))

	def closeEvent(self, event):
		self.settings.setValue("FindAndReplace/geometry", self.saveGeometry())
		QMainWindow.closeEvent(self, event)
