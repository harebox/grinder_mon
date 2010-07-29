#!/usr/env python
#
# Copyright (c) 2010  Hoonmin Kim <harebox@pinbook.net>
#
"""
grinder_mon : a simple incremental Grinder 3 log analyzer.

This is simplified version of Grinder Analyzer <http://track.sourceforge.net>,
written by Travis Bear.


usage :
1. Change 'dataset_prefix' value in grinder_mon.py
2. Run
	# cat data_grinder.log > python grinder_mon.py
3. Check output files.
	$dataset_prefix/tps.csv
	$dataset_prefix/response_time.csv

changelog :
2010.07.29
	* first public version
"""
dataset_prefix = '/home1/harebox/nginx/html/dataset'
dataset_postfix = '.csv'

import os
import sys
import time
import math
from cStringIO import StringIO

# Columns
COLUMN_THREAD = 0
COLUMN_RUN = 1
COLUMN_TEST = 2
COLUMN_START_TIME = 3
COLUMN_TEST_TIME = 4
COLUMN_ERRORS = 5
COLUMN_RESPONSE_TIME = 6
COLUMN_RESPONSE_LENGTH = 7
COLUMN_RESPONSE_ERRORS = 8
COLUMN_RESOLVE_TIME = 9
COLUMN_CONNECT_TIME = 10
COLUMN_FIRST_BYTE_TIME = 11

# Classes

class CsvAppender:
	"""CsvAppender"""
	tps_file = None
	response_time_file = None

	def __init__(self, statistics):
		self.statistics = statistics

		self.tps_file = open(dataset_prefix + '/tps' + dataset_postfix, 'w')
		self.response_time_file = open(dataset_prefix + '/response_time' + dataset_postfix, 'w')

		self.tps_file.write('Time,TPS\n')
		self.response_time_file.write('Time,Response Time\n')


	def __del__(self):
		self.tps_file.close()
		self.response_time_file.close()

	def append_tps(self):
		chunk = self.statistics.last_chunk()
		self.tps_file.write(chunk.to_tps_csv())
		self.tps_file.write('\n')
		self.tps_file.flush()

	def append_response_time(self):
		chunk = self.statistics.last_chunk()
		self.response_time_file.write(chunk.to_response_time_csv())
		self.response_time_file.write('\n')
		self.response_time_file.flush()


class Statistics:
	"""Statistics"""
	current_index = 0

	def __init__(self):
		self.chunks = {}
		self.ms_per_chunk = 1000
		self.base_time = None
		self.csv_appender = CsvAppender(self)

	def get_a_chunk(self, start_time):
		index = self.chunk_by_time(start_time)

		self.chunks.setdefault(index, Chunk(start_time))

		if self.current_index <= index:
			self.current_index = index

		return self.chunks[index]

	def last_chunk(self):
		return self.chunks[self.chunks.keys()[-2]]

	def chunk_by_time(self, time):
		if self.base_time == None:
			self.base_time = long(time)

		normalized_time = long(time) - self.base_time
		return int(math.floor(normalized_time / self.ms_per_chunk))

	def to_string(self):
		for k, v in self.chunks.iteritems():
			print v.to_string()


class Chunk:
	"""Chunk"""

	def __init__(self, start_time):
		self.tests = {}
		self.timestamp = long(start_time)

	def add_a_data(self, testno, columns):
		# refine data
		response_time = int(columns[COLUMN_RESPONSE_TIME])
		resolve_time = int(columns[COLUMN_RESOLVE_TIME])
		connect_time = int(columns[COLUMN_CONNECT_TIME])
		first_byte_time = int(columns[COLUMN_FIRST_BYTE_TIME])
		passed = True
		if columns[COLUMN_ERRORS].strip() != "0":
			passed = False
		bytes = long(columns[COLUMN_RESPONSE_LENGTH])

		# apply data
		self.tests.setdefault(testno, PerChunkStatistics(self))

		self.tests[testno].increase_pass_or_fail(passed)
		self.tests[testno].increase_bytes(bytes)
		self.tests[testno].increase_response_time(response_time)
		self.tests[testno].increase_resolve_time(resolve_time)
		self.tests[testno].increase_connect_time(connect_time)
		self.tests[testno].increase_first_byte_time(first_byte_time)

	def to_tps_csv(self):
		t = self.timestamp - statistics.base_time

		total_tps = 0.0
		for index, stat in self.tests.iteritems():
			total_tps += stat.calc.passed_tx_per_sec()


		str_buffer = StringIO()
		str_buffer.write('%d'%(t/1000.0))
		str_buffer.write(',%d'%(total_tps/len(self.tests.keys())))

		return str_buffer.getvalue()

	def to_response_time_csv(self):
		t = self.timestamp - statistics.base_time

		total_response_time = 0.0
		for index, stat in self.tests.iteritems():
			total_response_time += stat.calc.mean_response_time()

		str_buffer = StringIO()
		str_buffer.write('%d'%(t/1000.0))
		str_buffer.write(',%f'%(total_response_time/len(self.tests.keys())))

		return str_buffer.getvalue()

	def to_string(self):
		str_buffer = StringIO()
		for k, v in self.tests.iteritems():
			str_buffer.write('TEST %s (%d)\n'%(k, self.timestamp))
			str_buffer.write('%s\n\n'%v.to_string())
		return str_buffer.getvalue()


class PerChunkStatistics:
	"""PerChunkStatistics"""

	def __init__(self):
		self.calc = Calculator(self)
		self.total_pass = 0
		self.total_fail = 0
		self.total_received_bytes = 0
		self.total_response_time = 0
		self.total_resolve_time = 0
		self.total_connect_time = 0
		self.total_first_byte_time = 0

	def calc(self):
		return self.calc

	def increase_pass_or_fail(self, passed):
		if passed:
			self.total_pass += 1
		else:
			self.total_fail += 1

	def increase_bytes(self, bytes):
		self.total_received_bytes += bytes

	def increase_response_time(self, response_time):
		self.total_response_time += response_time

	def increase_resolve_time(self, resolve_time):
		self.total_resolve_time += resolve_time

	def increase_connect_time(self, connect_time):
		self.total_connect_time += connect_time

	def increase_first_byte_time(self, first_byte_time):
		self.total_first_byte_time += first_byte_time

	def to_string(self):
		str_buffer = StringIO()
		str_buffer.write('\ttotal_pass : %d\n'%self.total_pass)
		str_buffer.write('\ttotal_fail : %d\n'%self.total_fail)
		str_buffer.write('\ttotal_received_bytes : %d\n'%self.total_received_bytes)
		str_buffer.write('\ttotal_response_time : %d\n'%self.total_response_time)
		str_buffer.write('\ttotal_resolve_time : %d\n'%self.total_resolve_time)
		str_buffer.write('\ttotal_connect_time : %d\n'%self.total_connect_time)
		str_buffer.write('\ttotal_first_byte_time : %d\n'%self.total_first_byte_time)
		str_buffer.write('\t== summary ==\n')
		str_buffer.write(self.calc.to_string())
		return str_buffer.getvalue()


class Calculator:
	"""Calculator"""

	def __init__(self, per_chunk):
		self.per_chunk = per_chunk
	
	def passed_tx_per_sec(self):
		return self.per_chunk.total_pass * 1 / (statistics.ms_per_chunk / 1000.0)

	def failed_tx_per_sec(self):
		return self.per_chunk.total_fail * 1 / (statistics.ms_per_chunk / 1000.0)

	def mean_response_time(self):
		return self._mean(self.per_chunk.total_response_time)

	def mean_finish_time(self):
		return self._mean(self.per_chunk.total_response_time - self.per_chunk.total_first_byte_time)

	def mean_resolve_time(self):
		return self._mean(self.per_chunk.total_resolve_time)

	def mean_connect_time(self):
		return self._mean(self.per_chunk.total_connect_time)

	def mean_first_byte_time(self):
		return self._mean(self.per_chunk.total_first_byte_time)

	def mean_throughput_per_sec(self):
		seconds_per_chunk = statistics.ms_per_chunk / 1000.0
		bytes_per_kb = 1024.0

		return self.per_chunk.total_received_bytes * 1 / (bytes_per_kb * seconds_per_chunk)

	def _mean(self, total):
		total_pass = self.per_chunk.total_pass

		if total_pass != 0:
			return total / (total_pass * 1000.0)
		else:
			return 0.0

	def to_string(self):
		str_buffer = StringIO()
		
		str_buffer.write('\tpassed_tx_per_sec : %d\n'%self.passed_tx_per_sec())
		str_buffer.write('\tfailed_tx_per_sec : %d\n'%self.failed_tx_per_sec())
		str_buffer.write('\tmean_response_time : %f sec.\n'%self.mean_response_time())
		str_buffer.write('\tmean_finish_time : %f sec.\n'%self.mean_finish_time())
		str_buffer.write('\tmean_resolve_time : %f sec.\n'%self.mean_resolve_time())
		str_buffer.write('\tmean_connect_time : %f sec.\n'%self.mean_connect_time())
		str_buffer.write('\tmean_first_byte_time : %f sec.\n'%self.mean_first_byte_time())
		str_buffer.write('\tmean_throughput_per_sec : %f KB/sec.\n'%self.mean_throughput_per_sec())

		return str_buffer.getvalue()


# Utilities

def parse_a_line(line):
	return line.split(', ')


def read_data_from_pipe():
	line = sys.stdin.readline().strip()
	if not line or line == None:
		time.sleep(1)
		return -1, -1, None
	else:
		data = parse_a_line(line)
		testno = data[COLUMN_TEST]
		start_time = data[COLUMN_START_TIME]
		return testno, start_time, data
		

# Global

statistics = Statistics()

# Main

if __name__ == '__main__':
	prev_chunk = None

	while 1:
		# read data
		testno, start_time, data = read_data_from_pipe()

		# @TODO check for header line
		if not data[0].isdigit():
			continue

		# get(create) and update a chunk
		chunk = statistics.get_a_chunk(start_time)
		chunk.add_a_data(testno, data)

		# append a CSV line on change of the chunk.
		if prev_chunk != None and prev_chunk != chunk:
			statistics.csv_appender.append_tps()
			statistics.csv_appender.append_response_time()

		prev_chunk = chunk
