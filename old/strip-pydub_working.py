import wave, os, pydub, datetime

# Input file parameters (name & location)
input_filename_series = False
input_whole_folder = False
input_filename = 'cut-test-short.wav'
input_filename_list_range = range(228, 229)
input_filename_list = []
input_path = 'C:\Users\Alex\Google Drive\Ameryn\WTUL\Scripts'
output_path = 'C:\Users\Alex\Google Drive\Ameryn\WTUL\Scripts'
silence_thresh = -40

def strip_file(input_filename):

	input_filename_fullpath = os.path.join(input_path, input_filename)

	print 'BLOOOAAARRRRGHHGGGGHHHHH!!! (Please hold...)'
	ifile = wave.open(input_filename_fullpath)
	ifile_params = ifile.getparams()
	ofilename = input_filename.rsplit('.wav')[0]+'_stripped.wav'

	print input_filename_fullpath,'to', ofilename

	#pydub
	audio = pydub.AudioSegment.from_wav(input_filename)
	print audio.rms
	print audio.max
	print audio.max_possible_amplitude

	for ms_ord, ms in enumerate(audio):
		if ms.rms > 500:
			print "%d:%02d" % (divmod(ms_ord / 1000, 60)), ms.rms, '(%d dB)' % ms.dBFS
			break

	i = 0
	silence_chunk = 2000
	new_audio = None
	new_chunk_count = 0
	done = False

	while not done:
		if i+silence_chunk > len(audio):
			current_chunk = audio[i:]
			done = True
		else:
			current_chunk = audio[i:i+silence_chunk]
		if current_chunk.dBFS > silence_thresh:
			if not new_audio:
				print 'NOOOOOOOOO'
				new_audio = current_chunk
			else:
				new_audio += current_chunk
			new_chunk_count += 1
		print str(datetime.timedelta(milliseconds=i))+' - '+str(datetime.timedelta(milliseconds=i+silence_chunk))+': '+str(current_chunk.dBFS)+' dBFS'
		i += silence_chunk

	out_f = open(ofilename, 'wb')
	new_audio.export(out_f, format='wav')
	

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
	strip_file(each)