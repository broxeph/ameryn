import wave, os, pydub, datetime

# Input file parameters (name & location)
input_filename_series = False
input_whole_folder = False
input_filename = '06003_clean.wav'
input_filename_list_range = range(228, 229)
input_filename_list = []
input_path = 'C:\Users\Alex\Google Drive\Ameryn\WTUL\Scripts/tracky temp'
output_path = 'C:\Users\Alex\Google Drive\Ameryn\WTUL\Scripts/tracky temp'
silence_thresh = -45
audio_min_length = 30000
silence_min_length = 1000

def track_file(input_filename):
	i = 0
	new_audio = None
	markers = [0]	

	def add_marker(audio, ms):
		markers.append(ms)
		print 'Track', len(markers),'@', str(datetime.timedelta(milliseconds=ms))

	input_filename_fullpath = os.path.join(input_path, input_filename)
	output_filename_fullpath = os.path.join(output_path, input_filename)

	print 'BLOOOAAARRRRGHHGGGGHHHHH!!! (Please hold...)'
	print input_filename_fullpath,'to', output_filename_fullpath

	# pyDub open, amplitude stats
	audio = pydub.AudioSegment.from_wav(input_filename_fullpath)
	print audio.rms,'=', audio.dBFS*2, 'dBFS'
	print audio.max
	print audio.max_possible_amplitude

	# Detect first non-silence
	for ms_ord, ms in enumerate(audio):
		if ms.dBFS*2 > silence_thresh:
			print "%d:%02d" % (divmod(ms_ord / 1000, 60)), ms.rms, '(%d dB)' % (ms.dBFS*2)
			break

	# Detect tracks!
	while True:
		# Last track
		if i+silence_min_length > len(audio):
			current_chunk = audio[i:]
			add_marker(new_audio, len(audio))
			break		
		else:
			current_chunk = audio[i:i+silence_min_length]
			if i+silence_min_length*2 > len(audio):
				next_chunk = audio[i+silence_min_length:]
			else:
				next_chunk = audio[i+silence_min_length:i+silence_min_length*2]
		
		# If silent
		if current_chunk.dBFS*2 < silence_thresh:
			silent_chunk = '(Silent)'
			if i - markers[-1] >= audio_min_length and not next_chunk.dBFS*2 < silence_thresh:
				add_marker(new_audio, i + silence_min_length)
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
	
	#out_f = open(output_filename_fullpath, 'wb')
	#new_audio.export(out_f, format='wav')


# Make input filename list
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