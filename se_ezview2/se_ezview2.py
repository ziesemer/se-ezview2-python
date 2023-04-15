# Mark A. Ziesemer, 2023-01-28 - 2023-04-15

# - https://peps.python.org/pep-0563/
from __future__ import annotations

import collections.abc

import datetime
import enum
import typing

class EZView(collections.abc.Sequence):

	def __init__(self, file: typing.BinaryIO):
		self._file = file

		header = file.read(32)
		if header != (b"EZView2" + (b"\x00" * 25)):
			raise ValueError("EZView2 header missing.")

		self._header_size = int.from_bytes(file.read(4), "little") # Typically 36.
		self._data_offset = 32 + self._header_size # Typically 68.

		self._header_version = int.from_bytes(file.read(4), "little") # Typically 1.
		self._device_type = int.from_bytes(file.read(4), "little")
		self._record_count = int.from_bytes(file.read(4), "little")
		self._record_size = int.from_bytes(file.read(4), "little") # Typically 8.

		if self._device_type == 0:
			self._microseconds_multiply = 100
		else:
			self._microseconds_multiply = 1

		self._time_start = self._from_w32_file_time()

		# The data file format has an absolute timestamp (in Win32 format) before the typical 8-byte data structure
		#   of the first row packet, even though one might think this should be able to be calculated from the
		#   time_start + offset contained within the first row packet.
		self._time_first = self._from_w32_file_time()

		# This is the 4 bytes for the time offset in the first row packet.
		# This would typically be expected to be 0; however, it seems to range greatly.
		# In the "EZ-ViewDemo.dat" provided with the software, this is 973476 * .1ms (97.3476s).
		# However, one real-world file capture has this as 3470618715 μs (0:57:50.618715s).
		# Possibly a case of uninitialized memory in EZView?
		self._time_correct = datetime.timedelta(
			microseconds=int.from_bytes(file.read(4), "little") * self._microseconds_multiply)

		# time_offset is added to the time offset in each row packet before being returned.
		# Setting this to at least -time_correct is required to account for the discrepancies notes in the time_correct above.
		# Simply setting this to -time_correct would result in the first row having an offset of exactly 0.
		# While this may typically be expected, EZView shows the first row in relative time as the amount of time
		#   since the program has been launched - so including that difference here to maintain compatibility with the UI.
		self._time_offset = (self._time_first - self._time_start - self._time_correct)

	@property
	def header_size(self) -> int:
		return self._header_size

	@property
	def header_version(self) -> int:
		return self._header_version

	@property
	def device_type(self) -> int:
		return self._device_type

	@property
	def record_size(self) -> int:
		return self._record_size

	@property
	def time_start(self) -> datetime.datetime:
		return self._time_start

	@property
	def time_first(self) -> datetime.datetime:
		return self._time_first

	@property
	def time_offset(self) -> datetime.timedelta:
		return self._time_offset

	def __len__(self) -> int:
		return self._record_count

	def _from_w32_file_time(self) -> datetime.datetime:
		t = int.from_bytes(self._file.read(8), "little")
		if not t:
			return datetime.datetime.min
		s, ns100 = divmod(t - 116444736000000000, 10000000)
		dt = datetime.datetime.utcfromtimestamp(s)
		dt = dt.replace(microsecond=(ns100 // 10))
		return dt

	@typing.overload
	def __getitem__(self, key: int) -> Row: ...

	@typing.overload
	def __getitem__(self, key: slice) -> list[Row]: ...

	# - https://peps.python.org/pep-0484/#function-method-overloading
	def __getitem__(self, key: typing.Union[int, slice]) -> typing.Union[Row, list[Row]]:
		if isinstance(key, slice):
			return [self[ii] for ii in range(*key.indices(len(self)))]
		if(key < 0):
			key += self._record_count

		row = self._get_row(key)
		return row

	# Overriding __iter__ is not strictly necessary here, but provides some optimization
	#   for performance to bypass the additional checks otherwise checked for each hit
	#   in __getitem__.
	def __iter__(self):
		i = 0
		try:
			while True:
				v = self._get_row(i)
				yield v
				i += 1
		except IndexError:
			return

	def _get_row(self, pos: int) -> Row:
		rs = self._record_size
		self._file.seek(self._data_offset + pos * rs)
		row = self._file.read(rs)
		if(len(row) < rs):
			raise IndexError
		return Row(pos, row, self._time_offset, self._microseconds_multiply)

	def __repr__(self) -> str:
		kws = [
			f"{f}={getattr(self, f)!r}" for f in [
				"header_size", "header_version", "device_type",
				"_record_count", "record_size",
				"time_start", "time_first", "_time_correct", "time_offset"]
		]
		inner = ", ".join(kws)
		return f"{type(self).__name__}({inner})"

class Row:
	"""Represents (encapsulates) a capture data packet - also referred to as a record, row, event, or line."""

	def __init__(self, row: int, data: bytes, offset: datetime.timedelta, microseconds_multiply: int):
		self._raw = data
		self._row = row

		time = int.from_bytes(data[0:4], "little") | (data[7] << 32)
		time *= microseconds_multiply
		self._time_offset = datetime.timedelta(microseconds=time) + offset

	@property
	def row(self) -> int:
		"""
		The EZView Line #, but -1.
		(This field uses typical 0-based indexing, shared by Python - while EZView shows line numbers starting at 1.)
		"""
		return self._row

	@property
	def time_offset(self) -> datetime.timedelta:
		"""The (relative) timestamp of the row as displayed by EZView - when it is not configured for Absolute Time."""
		return self._time_offset

	@property
	def type(self) -> typing.Union[RowType, int]:
		"""
		- 0 = Undefined
		- 1 = DTE data TX
		- 2 = DCE data TX
		- 3 = Data Error/Break condition
		- 4 = DTE handshaking status change
		- 5 = DCE handshaking status change
		"""
		t = self._raw[4]
		if t >= len(RowType):
			return t
		return RowType(t)

	@property
	def data(self) -> int:
		"""
		Data byte for DTE and DCE TX data events.

		Status byte for DTE and DCE ERror/Break condition:
		- Bit: Definition
		- 0: DTE break condition.
		- 1: DTE parity error.
		- 2: DTE framing error.
		- 3: DCE break condition.
		- 4: DCE parity error.
		- 5: DCE framing error.

		Status byte for DTE handshaking events:
		- Bit: Definition
		- 0: DTE RTS signal status, 1 = active.
		- 1: DTE DTR signal status, 1 = active.

		Status byte for DCE handshaking events:
		- Bit: Definition
		- 0: DCE CTS signal status, 1 = active.
		- 1: DCE DSR signal status, 1 = active.
		- 2: DCE CD signal status, 1 = active.
		- 3: DCE RI signal status, 1 = active.
		"""
		return self._raw[5]

	@property
	def controls(self) -> Controls:
		"""
		Current handshaking/control line values, 1 = active.
		- Bit: Definition
		- 0: RTS
		- 1: DTR
		- 2: CTS
		- 3: DSR
		- 4: DCD
		- 5: RI
		"""
		return Controls(self._raw[6])

	@property
	def rts(self) -> bool:
		"""Request To Send"""
		return bool(self._raw[6] & Controls.RTS)

	@property
	def dtr(self) -> bool:
		"""Data Terminal Ready"""
		return bool(self._raw[6] & Controls.DTR)

	@property
	def cts(self) -> bool:
		"""Clear To Send"""
		return bool(self._raw[6] & Controls.CTS)

	@property
	def dsr(self) -> bool:
		"""Data Set Ready"""
		return bool(self._raw[6] & Controls.DSR)

	@property
	def cd(self) -> bool: # pylint: disable=invalid-name
		"""(Data) Carrier Detect"""
		return bool(self._raw[6] & Controls.CD)

	@property
	def ri(self) -> bool: # pylint: disable=invalid-name
		"""Ring Indicator"""
		return bool(self._raw[6] & Controls.RI)

	def __repr__(self) -> str:
		kws = [*[
			f"{f}={getattr(self, f)!r}" for f in [
				"row", "time_offset", "type"]
		], *[
			f"{f}=0x{getattr(self, f):02x}" for f in [
				"data", "controls"]
		] , *[
			f"{f}={getattr(self, f):d}" for f in [
				"rts", "dtr", "cts", "dsr", "cd", "ri"]
		]]
		inner = ", ".join(kws)
		return f"{type(self).__name__}({inner})"

class RowType(enum.IntEnum):
	UNDEFINED = 0
	"""0: Undefined"""
	DTE_DTX = 1
	"""1: DTE data TX"""
	DCE_DTX = 2
	"""2: DCE data TX"""
	DATA_ERROR_BREAK = 3
	"""3: Data Error/Break condition"""
	DTE_HSC = 4
	"""4: DTE handshaking status change"""
	DCE_HSC = 5
	"""5: DCE handshaking status change"""

class Controls(enum.IntFlag):
	RTS = 0x1
	"""0: Request To Send"""
	DTR = 0x2
	"""1: Data Terminal Ready"""
	CTS = 0x4
	"""2: Clear To Send"""
	DSR = 0x8
	"""3: Data Set Ready"""
	CD = 0x10
	"""4: (Data) Carrier Detect"""
	RI = 0x20
	"""5: Ring Indicator"""
