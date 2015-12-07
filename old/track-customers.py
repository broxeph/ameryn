"""
Add tracks to customer orders.
(c) Ameryn Media LLC, 2015. All rights reserved.
"""

import wave
import os
import datetime
import struct
import multiprocessing
import csv
import shutil
from ConfigParser import ConfigParser

import pydub

import utils

CONFIG_LOCATION = 'ameryn.ini'

config = ConfigParser()
config.read(CONFIG_LOCATION)

# Input file parameters (name & location)
input_path = config.get('general', 'clean_path')
output_path = config.get('general', 'tracked_path')
db_path = config.get('general', 'db_path')
input_filename_series = config.getboolean('track-customers', 'input_filename_series')
input_whole_folder = config.getboolean('track-customers', 'input_whole_folder')
input_filename = config.get('track-customers', 'input_filename')
input_filename_list_start = config.get('track-customers', 'input_filename_list_start')
input_filename_list_end = config.get('track-customers', 'input_filename_list_end')
input_filename_list_range = (input_filename_list_start, input_filename_list_end)
input_filename_list = []
silence_thresh = config.getint('track-customers', 'silence_thresh')
audio_min_length = config.getint('track-customers', 'audio_min_length')
silence_min_length = config.getint('track-customers', 'silence_min_length')
interside_silence_min_length = config.getint('track-customers', 'interside_silence_min_length')
pool_processing = config.getboolean('track-customers', 'pool_processing')

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
            if i + audio_min_length > len(audio):
                # Last track
                current_chunk = audio[i:]
                new_marker = len(audio)
                markers.append(new_marker)
                return markers       
            else:
                # Load next chunk
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
            #print 'i:', i, '| current_chunk:', mid + i*interside_silence_min_length, '-', mid + (i+1)*interside_silence_min_length,
            #    '| dBFS:', current_chunk.dBFS
            # If silent
            if current_chunk.dBFS < silence_thresh:
                markers.extend([mid + i*interside_silence_min_length, len(audio)])
                break
            # Down
            current_chunk = audio[mid - (i+1)*interside_silence_min_length:mid - i*interside_silence_min_length]
            #print 'i:', i, '| current_chunk:', mid - (i+1)*interside_silence_min_length, '-', mid - i*interside_silence_min_length,
            #   '| dBFS:', current_chunk.dBFS
            # If silent
            if current_chunk.dBFS < silence_thresh:                                
                markers.extend([mid - i*interside_silence_min_length, len(audio)])
                break
        else:
            # No silence found below silence_thresh and over interside_silence_min_length
            markers.extend([mid, len(audio)])
        return markers

    # Add '_tracked' suffix
    output_filename = os.path.splitext(os.path.basename(input_filename))[0].rsplit('_clean')[0].rsplit('_stripped')[0] + '_tracked.wav'

    input_filename_fullpath = os.path.join(input_path, input_filename)
    output_filename_fullpath = os.path.join(output_path, output_filename)

    print 'BLOOOAAARRRRGHHGGGGHHHHH!!! (Please hold...)'
    print input_filename_fullpath,'->', output_filename_fullpath

    # Detect over-CD-length audio (78:20)
    with open(db_path, 'r') as db:
        rows = csv.reader(db)
        audio_serial = os.path.basename(input_filename_fullpath).rsplit('_clean')[0].rsplit('_stripped')[0]
        for row in rows:
            if row[0] == audio_serial:
                if 'std' not in row[4].lower():
                    audio = pydub.AudioSegment.from_wav(input_filename_fullpath)
                    markers = detect_tracks()
                    break
                elif 'cd' not in row[5].lower():
                    print '{0} skipped: std digital'.format(audio_serial)
                else:
                    audio = pydub.AudioSegment.from_wav(input_filename_fullpath)
                    if len(audio) > 4700000:
                        markers = detect_std_cd_sides()
                        break
                    else:
                        print '{0} skipped: <78m std CD'.format(audio_serial)
                shutil.copy2(input_filename_fullpath, output_filename_fullpath)
                return
        else:
            raise Exception('Row {0} not found in {1}.'.format(audio_serial, db_path))

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

def main(input_filename_list=[]):
    # Make input filename list
    if input_filename_series and input_whole_folder:
        raise Exception("Series or folder. Can't have both. Sorry.")
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
        pool.map(track_file, pool_array)
    else:
        for item in pool_array:
            track_file(item)

if __name__ == '__main__':
    main()