"""
Add tracks to customer orders.
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
interside_silence_min_length = 3000
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
                #print 'Cue', num, 'written @', cue, '/', new._nframes, '(' + str(round(cue/float(new._nframes)*100, 2)) + '%)'
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

    def detect_tracks():
        markers = [0]
        i = 0
        while True:
            # Last track
            if i + silence_min_length > len(audio):
                current_chunk = audio[i:]
                new_marker = len(audio)
                markers.append(new_marker)
                return markers       
            else:
                current_chunk = audio[i:i + silence_min_length]
                if i + silence_min_length*2 > len(audio):
                    next_chunk = audio[i + silence_min_length:]
                else:
                    next_chunk = audio[i + silence_min_length:i + silence_min_length*2] 

            # If silent
            if current_chunk.dBFS < silence_thresh:
                if i - markers[-1] >= audio_min_length and not next_chunk.dBFS < silence_thresh:
                    new_marker = i + silence_min_length
                    markers.append(new_marker)
            i += silence_min_length

    def detect_std_cd_sides():
        markers = [0]
        mid = len(audio) / 2
        print 'mid:', mid
        for i in range(len(audio) / interside_silence_min_length / 2):
            # Up
            current_chunk = audio[mid + i*interside_silence_min_length:mid + (i+1)*interside_silence_min_length]
            #print 'i:', i, '| current_chunk:', mid + i*interside_silence_min_length, '-', mid + (i+1)*interside_silence_min_length, '| dBFS:', current_chunk.dBFS
            # If silent
            if current_chunk.dBFS < silence_thresh:
                markers = [mid + i*interside_silence_min_length]
            # Down
            current_chunk = audio[mid - (i+1)*interside_silence_min_length:mid - i*interside_silence_min_length]
            #print 'i:', i, '| current_chunk:', mid - (i+1)*interside_silence_min_length, '-', mid - i*interside_silence_min_length, '| dBFS:', current_chunk.dBFS
            # If silent
            if current_chunk.dBFS < silence_thresh:                                
                markers.extend([mid - i*interside_silence_min_length, len(audio)])
                break
        else:
            # No silence found below silence_thresh and over interside_silence_min_length
            markers.extend([mid, len(audio)])
        return markers

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

    # Detect over-CD-length audio (78:20)
    with open(db_path, 'r') as db:
        rows = csv.reader(db)
        audio_serial = os.path.basename(input_filename_fullpath).rsplit('_clean')[0]
        for row in rows:
            if row[0] == audio_serial:
                if 'cd' in row[5].lower() and 'std' in row[4].lower() and len(audio) > 4700000:
                    markers = detect_std_cd_sides()
                    break
                elif 'std' in row[4].lower():
                    print '{0} skipped: std'.format(audio_serial)
                    return
                else:
                    markers = detect_tracks()
                    break
        else:
            print 'Row', audio_serial, 'not found in', db_path + '.'        

    # Marker stats
    print 'Markers:', markers
    for num, marker in enumerate(markers):
        # Last marker
        if num == len(markers) - 1:
            track_length = 0
        else:
            track_length = round(markers[num + 1] - markers[num], -3)
        print 'Marker', num+1, '@', str(datetime.timedelta(milliseconds=round(marker, -3))), '(length:', str(datetime.timedelta(milliseconds=track_length))+')'    

    # Dooo itt
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

    # RUN THE TRAP    
    pool_array = [os.path.join(input_path, each) for each in input_filename_list]
    
    #for item in pool_array:
    #    track_file(item)

    pool = multiprocessing.Pool(multiprocessing.cpu_count() - 1)
    pool.map(track_file, pool_array)