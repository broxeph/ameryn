"""
Add tracks to customer orders,
splits 78+ min recordings into one file for each side.
(c) Ameryn Media, 2015. All rights reserved.
"""

import wave, os, pydub, datetime, struct
import multiprocessing
import csv

# Input file parameters (name & location)
input_filename_series = False
input_whole_folder = True
input_filename = '4-track.wav'
input_filename_list_range = ('00106', '00109-2')
input_filename_list = []
input_path = 'D:/00 Recorded/cdsplit/'
output_path = 'D:/00 Recorded/trackt/'
silence_thresh = -45
audio_min_length = 30000
silence_min_length = 1500
db_path = 'C:/Sextus share/items.csv'

def track_file(input_filename):
    def write_marked_file(output_filename_fullpath, audio, cues):
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
        """
        Write new file with markers
        """
        cue_offsets = [int(cue * 44.1) for cue in cues]
        new = wave.open(output_filename_fullpath, 'wb')
        new._write_header = write_header_new
        new.setnchannels(audio.channels)
        new.setsampwidth(audio.sample_width)
        new.setframerate(audio.frame_rate)
        new.setnframes(int(audio.frame_count()))
        new.writeframesraw(audio._data)
        new.close()

    i = 0
    markers = [0]
    cd_counter = 0

    print 'input_filename:', input_filename

    # Add suffix for same-folder output (Can't overwrite)
    if input_path == output_path:
        output_filename = os.path.splitext(os.path.basename(input_filename))[0]+'_tracked.wav'
    else:
        output_filename = os.path.basename(input_filename)

    input_filename_fullpath = os.path.join(input_path, input_filename)
    output_filename_fullpath = os.path.join(output_path, output_filename)

    print 'BLOOOAAARRRRGHHGGGGHHHHH!!! (Please hold...)'
    print input_filename_fullpath,'->', output_filename_fullpath

    # pyDub open, amplitude stats
    audio = pydub.AudioSegment.from_wav(input_filename_fullpath)
    print 'audio.rms =', audio.rms,'=', round(audio.dBFS, 2), 'dBFS'

    # Detect first non-silence
    for ms_ord, ms in enumerate(audio):
        if ms.dBFS > silence_thresh:
            print 'First non-silent slice: %d:%02d' % (divmod(ms_ord / 1000, 60)), ms_ord, 'ms =', ms.rms, '(%.2f dB)' % (ms.dBFS)
            break

    # Detect tracks!
    while True:
        # Last track
        if i + silence_min_length > len(audio):
            current_chunk = audio[i:]
            new_marker = len(audio)
            markers.append(new_marker)
            break       
        else:
            current_chunk = audio[i:i + silence_min_length]
            if i + silence_min_length*2 > len(audio):
                next_chunk = audio[i + silence_min_length:]
            else:
                next_chunk = audio[i + silence_min_length:i + silence_min_length*2]
        
        # If silent
        if current_chunk.dBFS < silence_thresh:
            silent_chunk = '(Silent)'
            if i - markers[-1] >= audio_min_length and not next_chunk.dBFS < silence_thresh:
                new_marker = i + silence_min_length
                markers.append(new_marker)
        else:
            silent_chunk = ''
        
        # Chunk dBFS stats
        #print str(datetime.timedelta(milliseconds=i))+' - '+str(datetime.timedelta(milliseconds=i+silence_min_length))+': '+str(round(current_chunk.dBFS, 2))+' dBFS', silent_chunk
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
    print input_filename_fullpath, '| Length:', len(audio),

    # Check CD-type xfer (not mp3)
    with open(db_path, 'r') as db:
        rows = csv.reader(db)
        audio_serial = os.path.basename(input_filename_fullpath).rsplit('_clean')[0]
        for row in rows:
            if row[0] == audio_serial:
                if 'cd' in row[5].lower():
                    # Check for CD-safe recording length (78:20)
                    if len(audio) > 4700000:
                        print '(Double!)'
                        if not cd_counter:
                            cd_counter = 1
                        # Write file for sides A and B
                        for i in range(2):
                            temp_filename = output_filename_fullpath.rsplit('_clean')[0] + '_' + str(cd_counter) + '_clean.wav'
                            print 'temp_filename:', temp_filename
                            split_point = 8
                            if i == 0:
                                split_markers = markers[:split_point]
                                split_audio = audio[:markers[split_point]]
                            else:
                                split_markers = [marker - markers[split_point] for marker in markers[split_point:]]
                                split_audio = audio[markers[split_point]:]
                            write_marked_file(temp_filename, split_audio, split_markers)
                            cd_counter += 1
                        return
                break
        else:
            print 'Row', audio_serial, 'not found in', db_path + '.'

    # Normal-length audio tracking
    write_marked_file(output_filename_fullpath, audio, markers)
    return

if __name__ == '__main__':
    # Make input filename list
    if input_filename_series and input_whole_folder:
        print 'Series or folder. Can\'t have both. Sorry.'
        raise SystemError
    if input_filename_series:
        for g in os.listdir(input_path):
            if g.startswith(input_filename_list_range[0]):
                list_started = True
            if g.endswith('.wav') and list_started is True:
                input_filename_list.append(g)
                # If end of range reached
                if g.startswith(input_filename_list_range[1]):
                    break
        print 'Input filenames (series) ({0}):'.format(len(input_filename_list)), input_filename_list
    elif input_whole_folder:
        for f in os.listdir(input_path):
            if f.endswith('.wav'):
                input_filename_list.append(f)
        print 'Input filenames (folder) ({0}):'.format(len(input_filename_list)), input_filename_list
    else:
        input_filename_list = [input_filename]

    # Remove Standard items
    input_filename_list_temp = []
    with open(db_path, 'r') as db:
        rows = csv.reader(db)  
        for item in input_filename_list:
            audio_serial = os.path.basename(item).rsplit('_clean')[0]
            db.seek(0)
            for row in rows:
                if row[0] == audio_serial:
                    if 'std' in row[4].lower():
                        print item, 'skipped: std'
                        break
                    elif 'del' in row[4].lower():
                        print item, '({0})'.format(row[4].lower())
                    elif '45' in row[3]:
                        print item, '({0})'.format(row[3])
                    input_filename_list_temp.append(item)
                    break
            else:
                print 'Row', audio_serial, 'not found in', db_path + '.'
    input_filename_list = input_filename_list_temp

    # RUN THE TRAP
    pool_array = [os.path.join(input_path, each) for each in input_filename_list]
    print 'To be tracked: ({0}):'.format(len(pool_array)), pool_array

    pool = multiprocessing.Pool(multiprocessing.cpu_count() - 1)
    pool.map(track_file, pool_array)