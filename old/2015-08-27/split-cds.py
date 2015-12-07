"""
Splits 78+ min recordings into one file for each side.
(c) Ameryn Media, 2015. All rights reserved.
"""

import wave
import os
import pydub
import datetime
import struct
import multiprocessing
import csv
from ConfigParser import ConfigParser

from split import read_markers
import utils

CONFIG_LOCATION = 'ameryn.ini'
config = ConfigParser()
config.read(CONFIG_LOCATION)

# Input file parameters (name & location)
input_filename_series = config.getboolean('split-cds', 'input_filename_series')
input_whole_folder = config.getboolean('split-cds', 'input_whole_folder')
input_filename = config.get('split-cds', 'input_filename')
input_filename_list_start = config.get('split-cds', 'input_filename_list_start')
input_filename_list_end = config.get('split-cds', 'input_filename_list_end')
input_filename_list_range = (input_filename_list_start, input_filename_list_end)
input_path = config.get('general', 'tracked_path')
output_path = config.get('split-cds', 'output_path')
silence_thresh = config.getint('split-cds', 'silence_thresh')
audio_min_length = config.getint('split-cds', 'audio_min_length')
silence_min_length = config.getint('split-cds', 'silence_min_length')
db_path = config.get('general', 'db_path')
pool_processing = config.getboolean('split-cds', 'pool_processing')

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

    input_filename_fullpath = os.path.join(input_path, input_filename)
    output_filename_fullpath = os.path.join(output_path, input_filename)

    # Check CD-type xfer (not mp3)
    with open(db_path, 'r') as db:
        rows = csv.reader(db)
        audio_serial = os.path.basename(input_filename_fullpath).rsplit('_clean')[0].rsplit('_tracked')[0]
        for row in rows:
            if row[0] == audio_serial:
                print '{0}?'.format(audio_serial)
                # Check for CD-safe recording length (78:20)
                if 'cd' in row[5].lower():
                    audio = pydub.AudioSegment.from_wav(input_filename_fullpath)
                    if len(audio) > 4700000:
                        print 'Double: {0}'.format(audio_serial)
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
                            return False, input_filename
                        for i in range(2):
                            temp_filename = output_filename_fullpath.rsplit('_clean')[0].rsplit('_tracked')[0] + '_' + str(cd_counter) + '_tracked.wav'
                            pydub_markers = [int(marker / 44.1) for marker in markers]                           
                            if i == 0:
                                split_markers = markers[:split_point + 1]
                                split_audio = audio[:pydub_markers[split_point]]
                            else:
                                split_markers = [marker - markers[split_point] for marker in markers[split_point:]]
                                split_audio = audio[pydub_markers[split_point]:]
                            write_marked_file(temp_filename, split_audio, split_markers)
                            cd_counter += 1
                        # Delete big original file
                        os.remove(input_filename_fullpath)
                        try:
                            os.remove(os.path.splitext(input_filename_fullpath)[0] + '.pkf')
                        except WindowsError:
                            pass
                        return True, None
                return False, None
        else:
            print 'Row', audio_serial, 'not found in', db_path + '.'
    return False, None

def main(input_filename_list=[], output_path=[]):
    needs_split_points = []
    split_files_counter = 0
    if not output_path or output_path.lower == 'none':
        output_path = input_path

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

    # Grab spreadsheet from Google Drive
    utils.export_csv('Items')

    # RUN THE TRAP
    pool_array = [os.path.join(input_path, each) for each in input_filename_list]

    if pool_processing:    
        pool = multiprocessing.Pool(multiprocessing.cpu_count() - 1)
        pool.map(split_cd, pool_array)
    else:
        for each in pool_array:
            results = split_cd(each)
            split_files_counter += results[0]
            if results[1]: needs_split_points.append(results[1])

    if needs_split_points:
        print 'Needs split points:', needs_split_points
    else:
        print 'CD splitting: great success! {0} files split.'.format(split_files_counter)

if __name__ == '__main__':
    main()