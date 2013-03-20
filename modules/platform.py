# Petter Strandmark 2013.

import os

try:
	import win32com.client
except:
	win32com = None


def create_platform(main_file):
	if os.name == 'nt':
		return WindowsPlatform(main_file)
	else:
		return Platform()


class Platform:
	def can_install_shortcut(self):
		return False

	def install_shortcut(self):
		pass

	def has_shortcut(self):
		return False

	def uninstall_shortcut(self):
		pass


class WindowsPlatform:

	def __init__(self, main_file):
		self.this_dir      = os.path.dirname(os.path.abspath(main_file))
		self.send_to       = os.path.join(os.getenv('APPDATA'),
		                             'Microsoft',
		                             'Windows',
		                             'SendTo')
		self.shortcut_file = os.path.join(self.send_to,
		                                  "Sexton.lnk")
		self.icon_file     = os.path.join(self.this_dir,
		                                  'images',
		                                  'sexton.ico')

	def can_install_shortcut(self):
		if win32com is None:
			return False
		else:
			return True

	def install_shortcut(self):
		shell                 = win32com.client.Dispatch('WScript.Shell')
		shortcut              = shell.CreateShortCut(os.path.join(self.send_to,
		                                            'Sexton.lnk'))
		shortcut.Targetpath   = os.path.join(self.this_dir, 'sexton.pyw')
		shortcut.IconLocation = self.icon_file
		# Other possible options.
		#shortcut.Arguments = ''
		#shortcut.WorkingDirectory = r'C:\Program Files'
		#shortcut.WindowStyle = 1;
	    #shortcut.Hotkey = "CTRL+SHIFT+F"
		shortcut.save()

	def has_shortcut(self):
		return os.path.exists(self.shortcut_file)

	def uninstall_shortcut(self):
		os.unlink(self.shortcut_file)
