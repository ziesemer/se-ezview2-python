# Mark A. Ziesemer, 2023-01-28 - 2023-04-15

import collections.abc
import contextlib
import datetime
import hashlib
import io
import pathlib
import struct
import typing
import unittest

import se_ezview2.se_ezview2 as ev2

class EZViewSynTest():
	fmt = "<7s25x5I2Q" + ("I4B" * 2)

	@staticmethod
	def fmt_args() -> typing.List[typing.Any]:
		return [
			b'EZView2', # 0
			36, # 1: Size of Header
			1, # 2: Version,
			0, # 3: Device Type
			2, # 4: Number of Data Records
			8, # 5: Size of Each Data Record
			0, # 6: Data Collection Start Time
			0, # 7: Time of First Data Record
			0, 0, 0, 0, 0, #8: Data Record 1
			1, 0, 0, 0, 0 #13: Data Record 2
		]

class EZViewSynSingleTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		x = struct.pack(EZViewSynTest.fmt, *EZViewSynTest.fmt_args())
		f = io.BytesIO(x)
		cls.addClassCleanup(f.close)
		cls.ezv = ev2.EZView(f)

	def test_sequence(self):
		self.assertIsInstance(self.ezv, collections.abc.Sequence)

	def test_header_size(self):
		self.assertEqual(self.ezv.header_size, 36)

	def test_header_version(self):
		self.assertEqual(self.ezv.header_version, 1)

	def test_device_type(self):
		self.assertEqual(self.ezv.device_type, 0)

	def test_record_size(self):
		self.assertEqual(self.ezv.record_size, 8)

	def test_time_start(self):
		self.assertEqual(self.ezv.time_start, datetime.datetime.min)

	def test_time_first(self):
		self.assertEqual(self.ezv.time_first, datetime.datetime.min)

	def test_time_offset(self):
		self.assertEqual(self.ezv.time_offset, datetime.timedelta(0))

	def test_len(self):
		self.assertEqual(len(self.ezv), 2)

	def test_getitem_0(self):
		self.assertEqual(self.ezv[0].row, 0)

	def test_getitem_minus1(self):
		self.assertEqual(self.ezv[-1].row, 1)

	def test_getitem_slice(self):
		self.assertEqual(len(self.ezv[0:0]), 0)
		self.assertEqual(len(self.ezv[0:1]), 1)
		self.assertEqual(len(self.ezv[0:2]), 2)

	def test_iter(self):
		i = 0
		for row in self.ezv:
			self.assertEqual(row.row, i)
			i += 1
		self.assertEqual(i, 2)

	def test_repr(self):
		self.assertEqual(str(self.ezv),
			"EZView(header_size=36, header_version=1, device_type=0, _record_count=2, record_size=8, " \
				+ "time_start=datetime.datetime(1, 1, 1, 0, 0), " \
				+ "time_first=datetime.datetime(1, 1, 1, 0, 0), " \
				+ "_time_correct=datetime.timedelta(0), " \
				+ "time_offset=datetime.timedelta(0))")

	def test_row_row(self):
		self.assertEqual(self.ezv[0].row, 0)
		self.assertEqual(self.ezv[1].row, 1)

	def test_row_time_offset(self):
		self.assertEqual(self.ezv[0].time_offset, datetime.timedelta(0))
		self.assertEqual(self.ezv[1].time_offset, datetime.timedelta(microseconds=100))

	def test_row_time_absolute(self):
		self.assertEqual(self.ezv[0].time_offset + self.ezv.time_start,
			datetime.datetime.min)
		self.assertEqual(self.ezv[1].time_offset + self.ezv.time_start,
			datetime.datetime(1, 1, 1, microsecond=100))

	def test_row_type(self):
		self.assertEqual(self.ezv[0].type, 0)
		self.assertEqual(self.ezv[0].type, ev2.RowType.UNDEFINED)

	def test_row_data(self):
		self.assertEqual(self.ezv[0].data, 0x00)

	def test_row_repr(self):
		self.assertEqual(str(self.ezv[0]),
			"Row(row=0, time_offset=datetime.timedelta(0), type=<RowType.UNDEFINED: 0>, data=0x00, controls=0x00, "
			+ "rts=0, dtr=0, cts=0, dsr=0, cd=0, ri=0)")

class EZViewSynTests(unittest.TestCase):

	def __init__(self, *args, **kwargs) -> None:
		super().__init__(*args, **kwargs)
		self.fmt: str
		self.fmt_args: typing.List[typing.Any]

	def setUp(self):
		self.fmt = EZViewSynTest.fmt
		self.fmt_args = EZViewSynTest.fmt_args()

	@contextlib.contextmanager
	def syn(self) -> typing.Iterator[ev2.EZView]:
		x = struct.pack(self.fmt, *self.fmt_args)
		with io.BytesIO(x) as f:
			ezv = ev2.EZView(f)
			yield ezv

	def test_empty(self):
		with io.BytesIO(b"") as f:
			with self.assertRaisesRegex(ValueError, "^EZView2 header missing.$"):
				ev2.EZView(f)

	def test_dates(self):
		self.fmt_args[6] = 133170048000000000
		self.fmt_args[7] = 133198707061234560
		with self.syn() as ezv:
			self.assertEqual(ezv.time_start, datetime.datetime(2023, 1, 1, 0, 0))
			self.assertEqual(ezv.time_first, datetime.datetime(2023, 2, 3, 4, 5, 6, 123456))

	def test_device_type_0(self):
		with self.syn() as ezv:
			self.assertEqual(ezv.device_type, 0)
			self.assertEqual(ezv[0].time_offset, datetime.timedelta(0))
			self.assertEqual(ezv[1].time_offset, datetime.timedelta(milliseconds=0.1))

	def test_device_type_1(self):
		self.fmt_args[3] = 1
		with self.syn() as ezv:
			self.assertEqual(ezv.device_type, 1)
			self.assertEqual(ezv[0].time_offset, datetime.timedelta(0))
			self.assertEqual(ezv[1].time_offset, datetime.timedelta(microseconds=1))

	def test_row_types(self):
		avail_types = ["UNDEFINED", "DTE_DTX", "DCE_DTX", "DATA_ERROR_BREAK", "DTE_HSC", "DCE_HSC"]

		for ti, t in enumerate(avail_types):
			self.fmt_args[9] = ti
			with self.syn() as ezv:
				self.assertEqual(ezv[0].type, ti)
				self.assertEqual(ezv[0].type, getattr(ev2.RowType, t))

	def test_row_type_invalid(self):
		invalid = 6
		self.fmt_args[9] = invalid
		with self.syn() as ezv:
			self.assertEqual(ezv[0].type, invalid)

	def test_controls(self):
		avail_controls = ["RTS", "DTR", "CTS", "DSR", "CD", "RI"]

		for s in range(1 << len(avail_controls)):
			self.fmt_args[11] = s
			with self.syn() as ezv:
				for ci, c in enumerate(avail_controls):
					self.assertEqual(ezv[0].controls, s)
					on = bool(s & (1 << ci))
					self.assertEqual(getattr(ezv[0], c.lower()), on)
					self.assertEqual(getattr(ev2.Controls, c) in ezv[0].controls, on)

	def test_controls_unknown(self):
		invalid = 0xFF
		self.fmt_args[11] = invalid
		with self.syn() as ezv:
			self.assertEqual(ezv[0].controls, invalid)

	def test_getitem_slice(self):
		self.fmt += "I4B" * 10
		self.fmt_args[4] = 12
		self.fmt_args.extend([0] * 50)
		with self.syn() as ezv:
			s = ezv[0:12:3]
			self.assertEqual(len(s), 4)
			# pylint: disable=unsubscriptable-object
			# - Possibly https://github.com/pylint-dev/pylint/issues/3637 ?
			self.assertEqual(s[0].row, 0)
			self.assertEqual(s[1].row, 3)
			self.assertEqual(s[2].row, 6)
			self.assertEqual(s[3].row, 9)

	def test_alternate_record_size(self):
		self.fmt_args[5] = 12
		self.fmt = self.fmt[:10] + ("I8B" * 2)
		self.fmt_args = self.fmt_args[:8]
		self.fmt_args.extend([0, 0, 12, *[0] * 6, 345, 0, 67, *[0] * 6])

		with self.syn() as ezv:
			self.assertEqual(ezv[0].time_offset, datetime.timedelta(0))
			self.assertEqual(ezv[0].data, 12)
			self.assertEqual(ezv[1].time_offset, datetime.timedelta(microseconds=34500))
			self.assertEqual(ezv[1].data, 67)

	def test_alternate_header_size(self):
		self.fmt = self.fmt[:10] + "36x" + self.fmt[10:]
		self.fmt_args[1] = 72

		with self.syn() as ezv:
			self.assertEqual(ezv[1].time_offset, datetime.timedelta(microseconds=100))

class EZViewSampleTests(unittest.TestCase):
	"""
	These tests require the EZ-ViewDemo.dat as provided with an an EZ-View application download.
	These tests are specific to the version distributed with version 1.6.90.
	It can be obtained from the installation directory after installing EZ-View	\
		using the	respective installer from \
		https://stratusengineering.com/downloads/, such as \
		https://stratusengineering.com/wp-content/uploads/2019/09/EZView_1_6_9.zip.
	"""

	@classmethod
	def setUpClass(cls):
		p = cls.sample_path = pathlib.Path("Samples/EZ-ViewDemo.dat")
		if not p.exists():
			raise unittest.SkipTest(f"{p} does not exist; please provide from an EZ-View application download.")
		f = open(p, "rb") # pylint: disable=consider-using-with
		cls.addClassCleanup(f.close)
		cls.ezv = ev2.EZView(f)

	def test_checksum(self):
		with open(self.sample_path, "rb") as f:
			d = hashlib.file_digest(f, "sha256")
		h = d.hexdigest()
		self.assertEqual(h, "d1df40da597d11e3e5055789424ead81da1771363ca0e1f376eae9d86ec125df")

	def test_header_size(self):
		self.assertEqual(self.ezv.header_size, 36)

	def test_header_version(self):
		self.assertEqual(self.ezv.header_version, 1)

	def test_device_type(self):
		self.assertEqual(self.ezv.device_type, 0)

	def test_record_size(self):
		self.assertEqual(self.ezv.record_size, 8)

	def test_time_start(self):
		self.assertEqual(self.ezv.time_start, datetime.datetime.min)

	def test_time_first(self):
		self.assertEqual(self.ezv.time_first, datetime.datetime.min)

	def test_time_offset(self):
		self.assertEqual(self.ezv.time_offset, datetime.timedelta(days=-1, seconds=86302, microseconds=652400))

	def test_len(self):
		self.assertEqual(len(self.ezv), 600)

	def test_getitem_0(self):
		self.assertEqual(self.ezv[0].row, 0)

	def test_getitem_minus1(self):
		self.assertEqual(self.ezv[-1].row, 599)

	def test_getitem_slice(self):
		self.assertEqual(len(self.ezv[0:0]), 0)
		self.assertEqual(len(self.ezv[0:1]), 1)
		self.assertEqual(len(self.ezv[0:2]), 2)
		self.assertEqual(len(self.ezv[0:12:3]), 4)

	def test_iter(self):
		i = 0
		for row in self.ezv:
			self.assertEqual(row.row, i)
			i += 1
		self.assertEqual(i, 600)

	def test_repr(self):
		self.assertEqual(str(self.ezv),
			"EZView(header_size=36, header_version=1, device_type=0, _record_count=600, record_size=8, " \
				+ "time_start=datetime.datetime(1, 1, 1, 0, 0), " \
				+ "time_first=datetime.datetime(1, 1, 1, 0, 0), " \
				+ "_time_correct=datetime.timedelta(seconds=97, microseconds=347600), " \
				+ "time_offset=datetime.timedelta(days=-1, seconds=86302, microseconds=652400))")

	def test_row_row(self):
		self.assertEqual(self.ezv[0].row, 0)
		self.assertEqual(self.ezv[599].row, 599)

	def test_row_time_offset(self):
		self.assertEqual(self.ezv[0].time_offset, datetime.timedelta(0))
		self.assertEqual(self.ezv[599].time_offset, datetime.timedelta(seconds=12, milliseconds=485, microseconds=900))

	def test_row_time_absolute(self):
		self.assertEqual(self.ezv[0].time_offset + self.ezv.time_start,
			datetime.datetime.min)
		self.assertEqual(self.ezv[599].time_offset + self.ezv.time_start,
			datetime.datetime(1, 1, 1, second=12, microsecond=485900))

	def test_row_type(self):
		self.assertEqual(self.ezv[0].type, 1)
		self.assertEqual(self.ezv[0].type, ev2.RowType.DTE_DTX)
		self.assertEqual(self.ezv[599].type, 2)
		self.assertEqual(self.ezv[599].type, ev2.RowType.DCE_DTX)

	def test_row_data(self):
		self.assertEqual(self.ezv[0].data, 0xAA)
		self.assertEqual(self.ezv[599].data, 0xC0)

	def test_row_repr(self):
		self.assertEqual(str(self.ezv[0]),
			"Row(row=0, time_offset=datetime.timedelta(0), type=<RowType.DTE_DTX: 1>, data=0xaa, controls=0x00, "
			+ "rts=0, dtr=0, cts=0, dsr=0, cd=0, ri=0)")
