import wave, os, pydub, datetime

# Input file parameters (name & location)
input_filename_series = False
input_whole_folder = True
input_filename = '2s-test.wav'
input_filename_list_range = range(228, 229)
input_filename_list = []
input_path = 'C:\Users\Alex\Google Drive\Ameryn\WTUL\Scripts\strippy temp'
output_path = 'C:\Users\Alex\Google Drive\Ameryn\WTUL\Scripts\strippy temp\stript'
silence_thresh = -50

def strip_file(input_filename):

	input_filename_fullpath = os.path.join(input_path, input_filename)
	output_filename = input_filename.rsplit('.wav')[0]+'_stripped_'+str(silence_thresh)+'.wav'
	output_filename_fullpath = os.path.join(output_path, output_filename)

	print 'BLOOOAAARRRRGHHGGGGHHHHH!!! (Please hold...)'

	print input_filename_fullpath,'to', output_filename_fullpath

	#pydub
	audio = pydub.AudioSegment.from_wav(input_filename_fullpath)
	pydub.effects.normalize(audio)
	print audio.rms,'=', audio.dBFS*2, 'dBFS'
	print audio.max
	print audio.max_possible_amplitude

	for ms_ord, ms in enumerate(audio):
		if ms.dBFS*2 > silence_thresh:
			print "%d:%02d" % (divmod(ms_ord / 1000, 60)), ms.rms, '(%d dB)' % (ms.dBFS*2)
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
		if current_chunk.dBFS*2 > silence_thresh:
			if not new_audio:
				print 'NOOOOOOOOO'
				new_audio = current_chunk
			else:
				new_audio += current_chunk
			new_chunk_count += 1
		print str(datetime.timedelta(milliseconds=i))+' - '+str(datetime.timedelta(milliseconds=i+silence_chunk))+': '+str(current_chunk.dBFS*2)+' dBFS'
		i += silence_chunk

	out_f = open(output_filename_fullpath, 'wb')
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