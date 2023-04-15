# Python SE EZ-View Library

## Summary

A Python software library for working with native-format data files saved by EZ-View™ (EZView).  This is software from Stratus Engineering, Inc. (SE, <https://stratusengineering.com/>), designed for use with their excellent EZ-Tap™, EZ-Tap Pro™, and Versa-Tap™ products.  These are passive tap modules / bus analyzers / protocol analyzers for RS-232 serial port monitoring - including RS-422, RS-485, and HDLC with the Versa-Tap™.

## Background

The primary software provided for capturing and working with the data from the SE interfaces is their own EZ-View™ software, as further detailed at <https://stratusengineering.com/free-monitoring-software/> and <https://stratusengineering.com/downloads/>.

The EZ-View™ software provides a few options for saving or exporting captured data:

1. The default / native "Save Data" format saves to a proprietary but capable and efficient binary file format, assuming a `*.dat` file extension.
2. A "Save Data as Binary" option appears to be the least useful.  The only options it prompts for after prompting for a filename are 2 checkboxes to "Save DTE" and "Save DCE" (each side of the communication).  This saves the raw data bytes sent and received - but mangling both sides together as if they were one stream (assuming both options are checked) - and regardless, this discards the associated timestamps, control lines, and all other metadata associated with the capture.
3. A "Save Data as Text" option - which I initially and completely overlooked as a viable option, assuming it would be the same as the above but assuming a text-only encoding and unsuitable for other binary data streams.  To the contrary, this creates a field-delimited file (such as a CSV) - with options to include or exclude the column headers, choices for a field delimiter (tab, comma, space(s), or other / user defined), and options for which fields to include in the export.  Ultimately, the export identically represents the same data and format shown within the application window.

Ultimately, I needed to access the raw data captured and saved from EZ-View™ - including per-row metadata - in a scriptable fashion in order to reverse-engineer a RS-232 communications protocol used between components in an industrial system for further automated analysis.

Before discovering the actual capabilities of the "Save Data as Text" option, I had already started reverse-engineering the native binary file format. Outside of a few of the fields in the file header and the break/error conditions that I didn't have any samples for to reproduce, I already had most of the file format decoded and this project well underway.  In early 2023, I then also received from SE an email with the contents of [`EZView2.h`](EZView2.h) (filename and indentation were not provided / lost in transit, and are my own best renditions).

## Features

This library was written with at least an attempt to follow accepted Python standards and best practices.

1. Written to be efficient and scalable.  All provided operations run in constant-time.
	1. Opening from any [Binary I/O](https://docs.python.org/3/library/io.html#binary-i-o) (typically a file), random access and seeks are used - avoiding the need to copy complete capture contents to memory.  Data packets are individually read, and allows for processing of effectively unlimited file sizes.
	2. (This includes some assumptions of the underlying data source provided.)
2. Follows standard Python APIs wherever possible.
	1. For example, the `EZView` class extends [`collections.abc.Sequence`](https://docs.python.org/3/library/collections.abc.html#collections.abc.Sequence).  This supports the use of [`len`](https://docs.python.org/3/library/functions.html#len), list/array-like access using the subscript operator / index access ([subscriptions](https://docs.python.org/3/reference/expressions.html#subscriptions)) - including support for slicing ([slices](https://docs.python.org/3/glossary.html#term-slice)), and the other provided mixin methods.
3. Requires no external dependencies for runtime outside of the Python standard library (empty [`requirements.txt`](requirements.txt)).
4. Linting (static code analysis) using [pylint](https://github.com/pylint-dev/pylint).
5. Robust and unit-tested, including 100% unit test coverage.
	1. Written using [unittest](https://docs.python.org/3/library/unittest.html), but configured to run using [pytest](https://pytest.org), [coverage.py](https://coverage.readthedocs.io/), and [pytest-cov](https://github.com/pytest-dev/pytest-cov).

Overall, this is really quite a simple project - but may also serve as a potential template for future similar efforts.

## File Format Notes

### EZView2

The native binary file format includes `EZView2` at the beginning of the file - indicating the file format, somewhat separate from the EZ-View™ software (currently at version 1.6.90 as of this effort).  _(This is mostly being noted here to assist as keywords for web searches to assist others who may be looking for information around decoding this file format.)_

### Row Time Offset Limitation

I can't fault SE for prioritizing efficiency over spending more bytes towards allowing for representing longer time offsets per data packet / row / event.  The current format allocates 5 bytes for the time - 1 DWORD (4 bytes or 32 bits) at the beginning of a data packet, followed by 1 more byte as the most significant byte (MSB) at the end of each data packet.

With these 5 bytes as 40 bits, 2^40 = 1,099,511,627,776 ticks.  These are divided by 1 or 100 microseconds (μs), depending upon the device type signified in the header.  Assuming the higher resolution case of 1 μs:  1,099,511,627,776 / (1,000 μs / ms) / (1,000 ms / s) / (60 s / minute) / (60 minutes / hour) / (24 hours / day) = ~12.726 days (12d, 17h, 25m, ~11.63s).  (When using the 100 μs, this extends to over 1,272 days - or just shy of 3.5 years.)

When EZ-View™ performs a capture with a duration longer the ~12.7 or ~1,272 days as detailed above, it seamlessly overflows.  This was confirmed in a real-world capture.  The line / row numbers continue to increment as usual, but the time offset wraps around the maximum value and restarts at a relative 0.  This relative offset may optionally be shown in absolute time, in which it is simply calculated from the absolute timestamps stored in the header data - meaning the "absolute time" mode is just an alternate display representation, and will also represent the same overflow / wrap-around of time.

This library could potentially be extended to detect and account for these overflows - at least as long as there are no idle periods in the capture with no packets for the durations specified above.  For now, this library follows the functionality displayed by the official software.

## Author

Mark A. Ziesemer

* <https://www.ziesemer.com>
* <https://www.linkedin.com/in/ziesemer/>
