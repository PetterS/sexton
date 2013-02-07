
import os

class DataBuffer:
	def read(self, pos, length):
		return None, 0

	def length(self):
		return 0

	def flush(self):
		pass


class TestBuffer(DataBuffer):

	def __init__(self, length):
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

	def __init__(self, file_name):
		self.file_name = file_name
		self.buffer_max_length = 512 * 1024
		self.buffer = bytearray(self.buffer_max_length)
		self.read_into_buffer(0)

	def read_into_buffer(self, pos):
		#print "Reading file block: ", pos
		self.file_size = os.path.getsize(self.file_name)
		#print "-- file size:", self.file_size

		# TODO: handle file size changes.

		with open(self.file_name, 'rb') as f:
			f.seek(pos)

			self.buffer_length = self.buffer_max_length
			if pos + self.buffer_length > self.file_size:
				self.buffer_length = self.file_size - pos
			# TODO: Reuse bytearray each time.
			self.buffer = bytes(f.read(self.buffer_length))
			self.view = memoryview(self.buffer)
			self.buffer_start = pos

		#print "-- buffer start:", self.buffer_start, " length:", self.buffer_length

	def read(self, pos, length):
		# We cannot read past the end of the file.
		read_length = min(length, self.file_size - pos)
		# Is the requested interval outside the current buffer?
		if pos < self.buffer_start or pos + read_length > self.buffer_start + self.buffer_length:
			self.read_into_buffer(max(0, pos - self.buffer_max_length / 2))
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
