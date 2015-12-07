"""
Lists 78+ min recordings to enable side A track counting.
(c) Ameryn Media, 2015. All rights reserved.
"""

import wave, os, pydub
import multiprocessing
import csv
from split import read_markers

# Input file parameters (name & location)
input_filename_series = False
input_whole_folder = True
input_filename = '4-track.wav'
input_filename_list_range = ('00106', '00109-2')
input_filename_list = []
input_path = 'D:/00 Recorded/dev/'
db_path = 'C:/Sextus share/items.csv'

def check_audio(input_filename):
    input_filename_fullpath = os.path.join(input_path, input_filename)
    audio = pydub.AudioSegment.from_wav(input_filename_fullpath)
    audio_serial = os.path.basename(input_filename_fullpath).rsplit('_clean')[0]

    # Check CD-type xfer (not mp3)
    with open(db_path, 'r') as db:
        rows = csv.reader(db)
        for row in rows:
            if row[0] == audio_serial:
                # Check for Deluxe CD over safe recording length (78:20)
                if 'cd' in row[5].lower() and 'del' in row[4].lower() and len(audio) > 4700000:
                    print audio_serial
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

    #for each in pool_array:
    #    check_audio(each)

    pool = multiprocessing.Pool(multiprocessing.cpu_count() - 1)
    pool.map(check_audio, pool_array)