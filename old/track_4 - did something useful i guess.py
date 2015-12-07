import wave, os, pydub, datetime, struct

# Input file parameters (name & location)
input_filename_series = False
input_whole_folder = True
input_filename = '4-track.wav'
input_filename_list_range = range(6004, 6010)
input_filename_list = []
input_path = 'Q:\Recordings/1199 - anderson/clean'
output_path = 'Q:\Recordings/1199 - anderson/clean'
silence_thresh = -45
audio_min_length = 30000
silence_min_length = 1500

def track_file(input_filename):

	def write_header_new(initlength):
	    WAVE_FORMAT_PCM = 0x0001
	    assert not new._headerwritten
	    new._file.write('RIFF')
	    if not new._nframes:
	        new._nframes = initlength / (new._nchannels * new._sampwidth)
	    new._datalength = new._nframes * new._nchannels * new._sampwidth
	    new._form_length_pos = new._file.tell()
	    new._file.write(struct.pack('<L4s4sLHHLLHH',
	        36 + 24*len(cues) + 12 + new._datalength,
	        'WAVE',
	        'fmt ',
	        16,
	        WAVE_FORMAT_PCM,
	        new._nchannels,
	        new._framerate,
	        new._nchannels * new._framerate * new._sampwidth,
	        new._nchannels * new._sampwidth,
	        new._sampwidth * 8,
	        ))
	    # Cues chunk wrapper (length: 12 + 24n)
	    new._file.write(struct.pack('<4sLL',
	    	'cue ', #chunkID
	    	24*len(cues) + 4, #chunkDataSize
	    	len(cues))) #cuePointsCount
	    # Cue chunks (length: 24 each)
	    for num, cue in enumerate(cue_offsets):
	    	new._file.write(struct.pack('<LL4sLLL',
	    		num, #cuePointID
	    		cue, #playOrderPosition (no playlist) **According to the spec, this should be 0. But who reads specs, anyway?**
	    		'data', #dataChunkID (not silence)
	    		0, #chunkStart (standard 'data' chunk)
	    		0, #blockStart (uncompressed)
	    		cue)) #sampleOffset (cue position)
	    	print 'Cue', num, 'written @', cue, '/', new._nframes, '(' + str(round(cue/float(new._nframes)*100, 2)) + '%)'
	    # Data chunk header
	    new._data_length_pos = new._file.tell()
	    new._file.write(struct.pack('<4sL',
	    	'data',
	    	new._datalength))
	    new._headerwritten = True

	i = 0
	markers = [0]	

	# Add suffix for same-folder output (Can't overwrite)
	if input_path == output_path:
		output_filename = input_filename.split('.wav')[0]+'_tracked.wav'
	else:
		output_filename = input_filename

	input_filename_fullpath = os.path.join(input_path, input_filename)
	output_filename_fullpath = os.path.join(output_path, output_filename)

	print 'BLOOOAAARRRRGHHGGGGHHHHH!!! (Please hold...)'
	print input_filename_fullpath,'->', output_filename_fullpath

	# pyDub open, amplitude stats
	audio = pydub.AudioSegment.from_wav(input_filename_fullpath)
	print 'audio.rms =', audio.rms,'=', round(audio.dBFS*2, 2), 'dBFS'
	print 'audio.max =', audio.max
	print 'audio.max_possible_amplitude =', audio.max_possible_amplitude

	# Detect first non-silence
	for ms_ord, ms in enumerate(audio):
		if ms.dBFS*2 > silence_thresh:
			print 'First non-silent slice: %d:%02d' % (divmod(ms_ord / 1000, 60)), ms_ord, 'ms =', ms.rms, '(%.2f dB)' % (ms.dBFS*2)
			break

	# Detect tracks!
	while True:
		# Last track
		if i + silence_min_length > len(audio):
			current_chunk = audio[i:]
			new_marker = len(audio)
			markers.append(new_marker)
			print 'Track', len(markers),'@', str(datetime.timedelta(milliseconds=new_marker))
			break		
		else:
			current_chunk = audio[i:i + silence_min_length]
			if i + silence_min_length*2 > len(audio):
				next_chunk = audio[i + silence_min_length:]
			else:
				next_chunk = audio[i + silence_min_length:i + silence_min_length*2]
		
		# If silent
		if current_chunk.dBFS*2 < silence_thresh:
			silent_chunk = '(Silent)'
			if i - markers[-1] >= audio_min_length and not next_chunk.dBFS*2 < silence_thresh:
				new_marker = i + silence_min_length
				markers.append(new_marker)
				print 'Track', len(markers),'@', str(datetime.timedelta(milliseconds=new_marker))
		else:
			silent_chunk = ''
		
		# Chunk dBFS stats
		print str(datetime.timedelta(milliseconds=i))+' - '+str(datetime.timedelta(milliseconds=i+silence_min_length))+': '+str(round(current_chunk.dBFS*2, 2))+' dBFS', silent_chunk

		i += silence_min_length

	# Marker stats
	print 'Markers:', markers
	for num, marker in enumerate(markers):
		# Last marker
		if num == len(markers) - 1:
			track_length = 0
		else:
			track_length = round(markers[num + 1] - markers[num], -3)
		print 'Track', num+1, '@', str(datetime.timedelta(milliseconds=round(marker, -3))), '(length:', str(datetime.timedelta(milliseconds=track_length))+')'
	
	# Write new file with markers
	cues = markers
	cue_offsets = [int(cue * 44.1) for cue in cues]
	new = wave.open(output_filename_fullpath, 'wb')
	new._write_header = write_header_new
	new.setnchannels(audio.channels)
	new.setsampwidth(audio.sample_width)
	new.setframerate(audio.frame_rate)
	new.setnframes(int(audio.frame_count()))
	print '_headerwritten:', new._headerwritten
	print '_datawritten:', new._datawritten
	new.writeframesraw(audio._data)
	print '_headerwritten:', new._headerwritten
	print '_datawritten:', new._datawritten
	new.close()


# Make input filename list
if input_filename_series and input_whole_folder:
	print 'Series or folder. Can\'t have both. Sorry.'
	raise SystemError
if input_filename_series:
	for f in input_filename_list_range:
		f = str(f).zfill(5)
		for g in os.listdir(input_path):
			if g.startswith(f) and g.endswith('.wav'):
				input_filename_list.append(g)
	print 'Input filenames (series):', input_filename_list
elif input_whole_folder:
	for f in os.listdir(input_path):
		if f.endswith('.wav'):
			input_filename_list.append(f)
	print 'Input filenames (folder):', input_filename_list
else:
	input_filename_list = [input_filename]

# RUN THE TRAP
for each in input_filename_list:
	print each	
	track_file(each)