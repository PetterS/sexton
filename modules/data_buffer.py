# -*- coding: utf-8 -*-
#
# Petter Strandmark 2013.

import os
try:
	import pywintypes
	import win32file
except:
	win32file = None

class DataBuffer:
	def __init__(self):
		self.modified = False

	def read(self, pos, length):
		return None, 0

	def length(self):
		return 0

	def flush(self):
		pass

	def is_readonly(self):
		return True

	def set_modified(self):
		self.modified = True


class TestBuffer(DataBuffer):

	def __init__(self, length):
		DataBuffer.__init__(self)

		self.data_length = length
		self.buffer = bytes(self.data_length)
		self.view = memoryview(self.buffer)

	def read(self, pos, length):
		read_length = min(length, self.data_length - pos)
		return self.view[pos:], read_length

	def length(self):
		return self.data_length

	def max_read_length(self):
		return 0

	def flush(self):
		pass


class FileBuffer(DataBuffer):

	def __init__(self, file_name, readonly=True):
		DataBuffer.__init__(self)

		self.file_name = file_name
		self.buffer_max_length = 512 * 1024
		self.buffer = bytearray(self.buffer_max_length)
		self.read_into_buffer(0)

		self.readonly = readonly
		self.last_pos = -1
		self.last_length = -1

	def read_into_buffer(self, pos):
		#print "Reading file block: ", pos
		self.file_size = os.path.getsize(self.file_name)

		# TODO: handle file size changes.

		if self.modified:
			self.flush()

		with open(self.file_name, 'rb') as f:
			f.seek(pos)

			self.buffer_length = self.buffer_max_length
			if pos + self.buffer_length > self.file_size:
				self.buffer_length = self.file_size - pos
			# TODO: Reuse bytearray each time.
			self.buffer = bytearray(f.read(self.buffer_length))
			self.view = memoryview(self.buffer)
			self.buffer_start = pos
			self.modified = False

	def read(self, pos, length):

		# Is this the exact same call as previously?
		if pos == self.last_pos and length == self.last_length:
			return self.last_view, self.last_read_length

		self.last_pos = pos
		self.last_length = length

		# We cannot read past the end of the file.
		read_length = min(length, self.file_size - pos)
		# Is the requested interval outside the current buffer?
		if pos < self.buffer_start or pos + read_length > self.buffer_start + self.buffer_length:
			self.read_into_buffer(max(0, pos - self.buffer_max_length // 2))
			the_view = self.view[pos - self.buffer_start:]

			self.last_view = the_view
			self.last_read_length = read_length
			return the_view, read_length
		else:
			# Return a view into the current buffer.
			the_view = self.view[pos - self.buffer_start:]

			self.last_view = the_view
			self.last_read_length = read_length
			return the_view, read_length

	def length(self):
		return self.file_size

	def flush(self):
		# Don't write to the file if there are no changes.
		if not self.modified:
			return
		# If there has been changes, the buffer can not be
		# read-only.
		if self.readonly:
			raise Exception("Trying to write a read-only buffer.")

		# Open the file for writing.
		with open(self.file_name, 'wb') as f:
			f.seek(self.buffer_start)
			f.write(self.buffer)

		self.modified = False

	def is_readonly(self):
		return self.readonly

class DriveBuffer(DataBuffer):

	def __init__(self, drive_name):
		DataBuffer.__init__(self)

		self.drive_name = drive_name
		self.buffer_max_length = 512 * 1024
		self.buffer = bytearray(self.buffer_max_length)
		self.read_into_buffer(0)

	def read_into_buffer(self, pos):
		space = win32file.GetDiskFreeSpace(self.drive_name)
		self.bytes_per_sector = space[1]
		self.file_size = space[0] * space[1] * space[3]
		#print("Reading file block: ", pos)
		#print("-- {0} bytes per sector".format(self.bytes_per_sector))
		#print("-- drive size : {0:.2f} GB".format(self.file_size / 1024**3))

		try:
			drive_device_name = "\\\\.\\" + self.drive_name.strip("\\")
			hfile = win32file.CreateFile(drive_device_name,
			                             win32file.GENERIC_READ,
			                             win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
			                             None,
			                             win32file.OPEN_EXISTING,
			                             win32file.FILE_ATTRIBUTE_NORMAL | win32file.FILE_FLAG_RANDOM_ACCESS,
			                             None)
			# Set the read position. It is important that
			# we read a multiple of the sector size.
			win32file.SetFilePointer(hfile, pos, win32file.FILE_BEGIN)

			self.buffer_length = self.buffer_max_length
			if pos + self.buffer_length > self.file_size:
				self.buffer_length = self.file_size - pos

			result = win32file.ReadFile(hfile, self.buffer_length)
			win32file.CloseHandle(hfile)
		except pywintypes.error as err:
			if err.winerror == 5:
				raise Exception("Access denied.\n\nAdministrator privileges are required to open drives.\nUse File->Elevate Process.")
			else:
				raise Exception(err.strerror)

		self.buffer = result[1]
		self.view = memoryview(self.buffer)
		self.buffer_start = pos

	def read(self, pos, length):
		# We cannot read past the end of the file.
		read_length = min(length, self.file_size - pos)
		# Is the requested interval outside the current buffer?
		if pos < self.buffer_start or pos + read_length > self.buffer_start + self.buffer_length:
			# We want to read before the actual position to cache data.
			read_position = pos - self.buffer_max_length // 2
			# Move back to an even sector size.
			read_position -= read_position % self.bytes_per_sector
			self.read_into_buffer(max(0, read_position))
			#print "-- Start in view:", pos - self.buffer_start
			the_view = self.view[pos - self.buffer_start:]
			return the_view, read_length
		else:
			# Return a view into the buffer.
			the_view = self.view[pos - self.buffer_start:]
			return the_view, read_length

		return self.view[pos:], read_length

	def length(self):
		return self.file_size

	def flush(self):
		pass
