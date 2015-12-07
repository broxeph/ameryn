"""
Splits 78+ min recordings into one file for each side.
(c) Ameryn Media, 2015. All rights reserved.
"""

import wave, os, pydub, datetime, struct
import multiprocessing
import csv
from split import read_markers

# Input file parameters (name & location)
input_filename_series = False
input_whole_folder = True
input_filename = '4-track.wav'
input_filename_list_range = ('00106', '00109-2')
input_filename_list = []
input_path = 'D:/00 Recorded/trackt/'
out_path = None
silence_thresh = -45
audio_min_length = 30000
silence_min_length = 1500
db_path = 'C:/Sextus share/items.csv'

def split_cd(input_filename):
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
        cue_offsets = cues
        new = wave.open(output_filename_fullpath, 'wb')
        new._write_header = write_header_new
        new.setnchannels(audio.channels)
        new.setsampwidth(audio.sample_width)
        new.setframerate(audio.frame_rate)
        new.setnframes(int(audio.frame_count()))
        new.writeframesraw(audio._data)
        new.close()

    i = 0
    cd_counter = 0

    print 'input_filename:', input_filename

    if not out_path:
        output_path = input_path
    input_filename_fullpath = os.path.join(input_path, input_filename)
    output_filename_fullpath = os.path.join(output_path, input_filename)
    audio = pydub.AudioSegment.from_wav(input_filename_fullpath)

    # Check CD-type xfer (not mp3)
    with open(db_path, 'r') as db:
        rows = csv.reader(db)
        audio_serial = os.path.basename(input_filename_fullpath).rsplit('_clean')[0]
        for row in rows:
            if row[0] == audio_serial:
                # Check for CD-safe recording length (78:20)
                if 'cd' in row[5].lower() and len(audio) > 4700000:
                    print '(Double!)'
                    markers = read_markers(input_filename)
                    if not markers:
                        raise SystemError('Hey! {0} needs markers!'.format(audio_serial))
                    if not cd_counter:
                        cd_counter = 1
                    # Write file for sides A and B
                    if 'std' in row[4]:
                        if markers[0] == 0:
                            split_point = 1
                        else:
                            split_point = 0
                    elif row[10].startswith('_'):
                        split_point = int(row[10][1:3])
                    else:
                        split_point = 1
                    for i in range(2):
                        temp_filename = output_filename_fullpath.rsplit('_clean')[0] + '_' + str(cd_counter) + '_clean.wav'
                        pydub_markers = [int(marker / 44.1) for marker in markers]
                        print 'temp_filename:', temp_filename
                        print 'markers:', markers
                        print 'pydub_markers:', pydub_markers
                        print 'split_point:', split_point                            
                        if i == 0:
                            split_markers = markers[:split_point + 1]
                            split_audio = audio[:pydub_markers[split_point]]
                        else:
                            split_markers = [marker - markers[split_point] for marker in markers[split_point:]]
                            split_audio = audio[pydub_markers[split_point]:]
                        print 'split_markers:', split_markers
                        print 'len(split_audio):', len(split_audio)
                        write_marked_file(temp_filename, split_audio, split_markers)
                        cd_counter += 1
                    # Delete big original file
                    #os.remove(input_filename_fullpath)
                    #os.remove(os.path.splitext(input_filename_fullpath)[0] + '.pkf')
                    return
                break
        else:
            print 'Row', audio_serial, 'not found in', db_path + '.'
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
    print 'To be tracked: ({0}):'.format(len(pool_array)), pool_array

    for each in pool_array:
        split_cd(each)

    #pool = multiprocessing.Pool(multiprocessing.cpu_count() - 1)
    #pool.map(split_cd, pool_array)