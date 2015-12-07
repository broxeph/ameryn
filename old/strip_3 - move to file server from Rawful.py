"""
Strip silence from recorded audio, move to file server(s).
(c) Ameryn Media LLC, 2015. All rights reserved.
"""

import os
import datetime
from ConfigParser import ConfigParser
import shutil

import pydub


CONFIG_LOCATION = 'ameryn.ini'

config = ConfigParser()
config.read(CONFIG_LOCATION)

# Input file parameters (name & location)
overwrite_source = config.getboolean('strip', 'overwrite_source')
output_suffix = config.getboolean('strip', 'output_suffix')
input_path = config.get('strip', 'input_path')
output_path = config.get('strip', 'output_path')
silence_thresh = config.getint('strip', 'silence_thresh') # dBFS
silence_chunk = config.getint('strip', 'silence_chunk') # Seconds
recorded_archive = config.get('general', 'recorded_archive')

def strip_file(input_filename):
	input_filename_fullpath = os.path.join(input_path, input_filename)
	if overwrite_source:
		output_filename = input_filename
	elif output_suffix:
		output_filename = input_filename.rsplit('.wav')[0]+'_stripped.wav'
	else:
		output_filename = input_filename
	output_filename_fullpath = os.path.join(output_path, output_filename)
	print input_filename_fullpath,'->', output_filename_fullpath

	audio = pydub.AudioSegment.from_wav(input_filename_fullpath)

	i = 0
	new_audio = None
	done = False

	# Silence removal
	while not done:
		if i+silence_chunk > len(audio):
			# Last chunk
			current_chunk = audio[i:]
			done = True
		else:
			current_chunk = audio[i:i+silence_chunk]
		if current_chunk.dBFS > silence_thresh:
			if not new_audio:
				print 'NEWWWWWWWWW'
				new_audio = current_chunk
			else:
				new_audio += current_chunk
			print str(datetime.timedelta(milliseconds=i))+' - '+str(datetime.timedelta(milliseconds=i+silence_chunk))+': '+ \
				str(round(current_chunk.dBFS, 2))+' dBFS'
		else:
			print str(datetime.timedelta(milliseconds=i))+' - '+str(datetime.timedelta(milliseconds=i+silence_chunk))+': '+ \
				str(round(current_chunk.dBFS, 2))+' dBFS (Silence, below '+str(silence_thresh)+' dBFS)'
		i += silence_chunk

	# Export audio
	if new_audio:
		out_f = open(output_filename_fullpath, 'wb')
		new_audio.export(out_f, format='wav')
	else:
		silent_files.append(input_filename)

	# Move original .wav & .pkf files to Julius archive
	archive_path = os.path.join(recorded_archive, str(datetime.datetime.now().year) + '-' + str(datetime.datetime.now().month).zfill(2))
	if not os.path.isdir(archive_path):
		os.makedirs(archive_path)
	shutil.move(input_filename_fullpath, os.path.join(archive_path, input_filename))
	shutil.move(os.path.splitext(input_filename_fullpath)[0] + '.pkf', os.path.join(archive_path, os.path.splitext(input_filename)[0] + '.pkf'))

silent_files = []

# Make input filename list	
if overwrite_source:
	output_path = input_path
input_filename_list = [f for f in os.listdir(input_path) if f.endswith('.wav') and '_stripped' not in f]
print 'Input filenames (folder):', input_filename_list

# RUN THE TRAP
for each in input_filename_list:
	print each
	strip_file(each)

if silent_files:
	print
	print 'Silent files (re-record?):'
	for each in silent_files:
		print ' - ' + each