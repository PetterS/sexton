
from PySide import QtCore, QtGui, QtUiTools
from PySide.QtCore import *

try:
    from queue import Queue
except:
    from Queue import Queue


class Invoker(QObject):
    def __init__(self):
        super(Invoker, self).__init__()
        self.queue = Queue()

    def invoke(self, func, *args):
        f = lambda: func(*args)
        self.queue.put(f)
        QMetaObject.invokeMethod(self, "handler", QtCore.Qt.QueuedConnection)

    @Slot()
    def handler(self):
        f = self.queue.get()
        f()
invoker = Invoker()


def invoke_in_main_thread(func, *args):
    invoker.invoke(func, *args)


#
# Decorator to wrap a widget member function
# with a graphical exception display
#
import functools


def exception_handler(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        try:
            f(*args, **kwargs)
        except Exception as e:
            import os
            import sys
            import traceback
            self = args[0]
            # Extract last element (-1) of trace-back (2)
            tb = traceback.extract_tb(sys.exc_info()[2])[-1]
            # Add info to error string
            file_name = os.path.split(tb[0])[1]
            line = str(tb[1])
            error_string = 'Exception "' + e.__class__.__name__ + \
                           '" encountered.\n' + file_name +  \
                           ", line " + line + "\n" + f.__name__ + \
                           ':\n\n' + str(e)
            QtGui.QMessageBox.critical(self, 'Exception', error_string)
    return wrapper


#
# Main window class which loads UI files, supports settings, etc.
#
class PMainWindow(QtGui.QMainWindow):
    def __init__(self,
                 ui_file,
                 company_name,
                 app_name,
                 default_width=800,
                 default_height=300):
        QtGui.QMainWindow.__init__(self)

        # Set up UI
        loader = QtUiTools.QUiLoader()
        self.ui = loader.load(ui_file, None)
        self.setCentralWidget(self.ui)
        QtCore.QMetaObject.connectSlotsByName(self)

        # Size constraints
        self.setMinimumSize(self.ui.minimumSize())
        self.setMaximumSize(self.ui.maximumSize())
        self.resize(default_width, default_height)

        # Settings
        self.settings = QSettings(company_name, app_name)
        self.restoreGeometry(self.settings.value("Main/geometry"))

    def closeEvent(self, event):
        self.settings.setValue("Main/geometry", self.saveGeometry())

    def get_tree_header_width(self, tree, name):
        for c in range(tree.columnCount()):
            width = tree.columnWidth(c)
            width = self.settings.value('Trees/' + name + '/' + str(c), width)
            tree.setColumnWidth(c, int(width))

    def set_tree_header_width(self, tree, name):
        for c in range(tree.columnCount()):
            width = tree.columnWidth(c)
            self.settings.setValue('Trees/' + name + '/' + str(c), width)
