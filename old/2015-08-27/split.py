"""
Splits wave files based on cues (markers) in header, optionally exporting to mp3/FLAC with ffmpeg.
(c) Ameryn Media LLC, 2015. All rights reserved.
"""

import struct
import warnings
import wave
import os
from sys import byteorder, version_info, exit
import multiprocessing
import logging
import csv

import numpy
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error
from mutagen import File
from mutagen.flac import Picture
from pydub import AudioSegment
from send2trash import send2trash

import utils
import config


class WavFileWarning(UserWarning):
    pass


_big_endian = False
WAVE_FORMAT_PCM = 0x0001
WAVE_FORMAT_IEEE_FLOAT = 0x0003
WAVE_FORMAT_EXTENSIBLE = 0xfffe
KNOWN_WAVE_FORMATS = (WAVE_FORMAT_PCM, WAVE_FORMAT_IEEE_FLOAT)

input_filename_list = []
errors = []

# assumes file pointer is immediately after the 'fmt ' id
def _read_fmt_chunk(fid):
    if _big_endian:
        fmt = '>'
    else:
        fmt = '<'
    res = struct.unpack(fmt + 'iHHIIHH', fid.read(20))
    size, comp, noc, rate, sbytes, ba, bits = res
    if comp not in KNOWN_WAVE_FORMATS or size > 16:
        comp = WAVE_FORMAT_PCM
        warnings.warn("Unknown wave file format", WavFileWarning)
        if size > 16:
            fid.read(size - 16)

    return size, comp, noc, rate, sbytes, ba, bits

# assumes file pointer is immediately after the 'data' id
def _read_data_chunk(fid, comp, noc, bits, mmap=False):
    if _big_endian:
        fmt = '>i'
    else:
        fmt = '<i'
    size = struct.unpack(fmt, fid.read(4))[0]

    bytes_num = bits // 8
    if bits == 8:
        dtype = 'u1'
    else:
        if _big_endian:
            dtype = '>'
        else:
            dtype = '<'
        if comp == 1:
            dtype += 'i%d' % bytes_num
        else:
            dtype += 'f%d' % bytes_num
    if not mmap:
        data = numpy.fromstring(fid.read(size), dtype=dtype)
    else:
        start = fid.tell()
        data = numpy.memmap(fid, dtype=dtype, mode='c', offset=start, shape=(size // bytes_num,))
        fid.seek(start + size)

    if noc > 1:
        data = data.reshape(-1, noc)
    return data


def _skip_unknown_chunk(fid):
    if _big_endian:
        fmt = '>i'
    else:
        fmt = '<i'
    data = fid.read(4)
    # Zero-padding to avoid struct read errors
    data = '\0' * (4 - len(data)) + data
    size = struct.unpack(fmt, data)[0]
    # Print data
    fid.seek(size, 1)


def _read_riff_chunk(fid):
    global _big_endian
    str1 = fid.read(4)
    if str1 == b'RIFX':
        _big_endian = True
    elif str1 != b'RIFF':
        raise ValueError("Not a WAV file.")
    if _big_endian:
        fmt = '>I'
    else:
        fmt = '<I'
    fsize = struct.unpack(fmt, fid.read(4))[0] + 8
    str2 = fid.read(4)
    if (str2 != b'WAVE'):
        raise ValueError("Not a WAV file.")
    if str1 == b'RIFX':
        _big_endian = True
    return fsize


# open a wave-file
def read(filename, mmap=False):
    """
    Return the sample rate (in samples/sec) and data from a WAV file

    Parameters
    ----------
    filename : string or open file handle
        Input wav file.
    mmap : bool, optional
        Whether to read data as memory mapped.
        Only to be used on real files (Default: False)

        .. versionadded:: 0.12.0

    Returns
    -------
    rate : int
        Sample rate of wav file
    data : numpy array
        Data read from wav file

    Notes
    -----

    * The file can be an open file or a filename.

    * The returned sample rate is a Python integer
    * The data is returned as a numpy array with a
      data-type determined from the file.

    """
    if hasattr(filename, 'read'):
        fid = filename
        mmap = False
    else:
        fid = open(filename, 'rb')

    try:
        fsize = _read_riff_chunk(fid)
        noc = 1
        bits = 8
        comp = WAVE_FORMAT_PCM
        while fid.tell() < fsize:
            # read the next chunk
            chunk_id = fid.read(4)
            if chunk_id == b'fmt ':
                size, comp, noc, rate, sbytes, ba, bits = _read_fmt_chunk(fid)
            elif chunk_id == b'fact':
                _skip_unknown_chunk(fid)
            elif chunk_id == b'data':
                data = _read_data_chunk(fid, comp, noc, bits, mmap=mmap)
            elif chunk_id == b'LIST':
                # Someday this could be handled properly but for now skip it
                _skip_unknown_chunk(fid)
                warnings.warn("List chunk (non-data) not understood, skipping it.", WavFileWarning)
            elif chunk_id == b'cue ':
                # Someday this could be handled properly but for now skip it
                _skip_unknown_chunk(fid)
                warnings.warn("Cue chunk (non-data) not understood, skipping it.", WavFileWarning)
            else:
                warnings.warn("Chunk (non-data) not understood, skipping it.", WavFileWarning)
                _skip_unknown_chunk(fid)
    finally:
        if not hasattr(filename, 'read'):
            fid.close()
        else:
            fid.seek(0)

    return rate, data


# Write a wave-file
# sample rate, data
def write(filename, rate, data):
    """
    Write a numpy array as a WAV file

    Parameters
    ----------
    filename : string or open file handle
        Output wav file
    rate : int
        The sample rate (in samples/sec).
    data : ndarray
        A 1-D or 2-D numpy array of either integer or float data-type.

    Notes
    -----
    * The file can be an open file or a filename.

    * Writes a simple uncompressed WAV file.
    * The bits-per-sample will be determined by the data-type.
    * To write multiple-channels, use a 2-D array of shape
      (Nsamples, Nchannels).

    """
    if hasattr(filename, 'write'):
        fid = filename
    else:
        fid = open(filename, 'wb')

    try:
        dkind = data.dtype.kind
        if not (dkind == 'i' or dkind == 'f' or (dkind == 'u' and data.dtype.itemsize == 1)):
            raise ValueError("Unsupported data type '%s'" % data.dtype)

        fid.write(b'RIFF')
        fid.write(b'\x00\x00\x00\x00')
        fid.write(b'WAVE')
        # fmt chunk
        fid.write(b'fmt ')
        if dkind == 'f':
            comp = 3
        else:
            comp = 1
        if data.ndim == 1:
            noc = 1
        else:
            noc = data.shape[1]
        bits = data.dtype.itemsize * 8
        sbytes = rate * (bits // 8) * noc
        ba = noc * (bits // 8)
        fid.write(struct.pack('<ihHIIHH', 16, comp, noc, rate, sbytes, ba, bits))
        # data chunk
        fid.write(b'data')
        fid.write(struct.pack('<i', data.nbytes))
        if data.dtype.byteorder == '>' or (data.dtype.byteorder == '=' and byteorder == 'big'):
            data = data.byteswap()
        _array_tofile(fid, data)

        # Determine file size and place it in correct position at start of the file.
        size = fid.tell()
        fid.seek(4)
        fid.write(struct.pack('<i', size - 8))

    finally:
        if not hasattr(filename, 'write'):
            fid.close()
        else:
            fid.seek(0)


if version_info[0] >= 3:
    def _array_tofile(fid, data):
        # ravel gives a c-contiguous buffer
        fid.write(data.ravel().view('b').data)
else:
    def _array_tofile(fid, data):
        fid.write(data.tostring())


def read_markers(f, mmap=False):
    if hasattr(f, 'read'):
        fid = f
    else:
        fid = open(f, 'rb')
    fsize = _read_riff_chunk(fid)
    cues = []
    while (fid.tell() < fsize):
        chunk_id = fid.read(4)
        # print 'chunk_id:', chunk_id
        if chunk_id == b'cue ' or 'cue' in chunk_id:
            if chunk_id[-3:] == 'cue':  # Because Audition can't create cue chunks for crap
                fid.read(1)
            size, numcue = struct.unpack('<ii', fid.read(8))
            for c in range(numcue):
                id, position, datachunkid, chunkstart, blockstart, sampleoffset = struct.unpack('<iiiiii', fid.read(24))
                if sampleoffset not in cues:
                    cues.append(sampleoffset)
        elif chunk_id == b'_PMX':
            if chunk_id == 'totally implemented yo':
                print '_PMX!!'
                first = struct.unpack('<i', fid.read(4))[0]
                print 'first:', first
                text = fid.read(first)
                print 'text:', text
        else:
            _skip_unknown_chunk(fid)
    fid.close()
    return cues


def split_item(item, digital_folder=config.digital_folder, dropbox_move=True):
    logging.info('BLOOOAAARRRRGHHGGGGHHHHH!!! (Please hold...)')
    audio = wave.open(item.path)
    audio.params = audio.getparams()

    # Load AudioSegment for encoded segments
    if item.digital_ext is not 'wav':
        audio_segment = AudioSegment.from_wav(item.path)

    # Loop through cues and write regions (assumes start and end markers)
    for i, track in enumerate(item.tracks):
        # Build track filename
        digital_track_name = '{0} - {1} - {2}'.format(item.digital_file_name, str(i + 1), track.title)
        digital_track_name = digital_track_name.replace('/', '-')
        digital_track_name = ''.join(
            [c for c in digital_track_name if c.isalpha() or c.isdigit() or c in "'- ._()!@#$%^&*"]).rstrip('. ')
        if dropbox_move:
            digital_track_path = os.path.join(item.dropbox_order_folder, digital_track_name) + '.' + item.digital_ext
        else:
            digital_track_path = os.path.join(digital_folder, digital_track_name) + '.' + item.digital_ext
        logging.info('Region {0} | {1} -> {2}'.format(i + 1, track.duration, digital_track_path))
        # Split, export track
        if 'wav' not in item.digital_ext:
            digital_track = audio_segment[(item.cues[i] / 44.1):(item.cues[i + 1] / 44.1)]
            tags = {'title': track.title or 'Track {0}'.format(i + 1), 'artist': item.artist,
                    'albumartist': item.artist,
                    'album': (item.album or item.artist), 'track': (i + 1)}
            digital_track.export(out_f=digital_track_path, format=item.digital_ext, bitrate=item.bitrate, tags=tags, id3v2_version='3')
            # Add cover art
            if item.thumb and (item.digital_ext == 'mp3'):
                mutagen_audio = MP3(digital_track_path, ID3=ID3)
                try:
                    # Add ID3 tag if it doesn't exist
                    mutagen_audio.add_tags()
                except error:
                    pass
                mutagen_audio.tags.add(
                    APIC(
                        encoding=3,  # 3 is for utf-8
                        mime='image/jpeg',  # image/jpeg or image/png
                        type=3,  # 3 is for the cover image
                        desc=u'Cover',
                        data=open(item.thumb_path, 'rb').read()
                    )
                )
                mutagen_audio.save(v2_version=3)
            elif item.thumb and (item.digital_ext == 'flac'):
                mutagen_audio = File(digital_track_path)
                flac_image = Picture()
                flac_image.type = 3
                mime = 'image/jpeg'
                flac_image.desc = 'Cover'
                with open(item.thumb_path, 'rb') as f:
                    flac_image.data = f.read()
                mutagen_audio.add_picture(flac_image)
                mutagen_audio.save()
            else:
                logging.warning('No cover found for item {0}'.format(item.name))
        else:
            digital_track = wave.open(digital_track_path, 'w')
            digital_track.setparams(audio.params)
            region_length = item.cues[i + 1] - item.cues[i]
            digital_track.writeframes(audio.readframes(region_length))
            digital_track.close()
    audio.close()


def split_file(input_filename, export_format='flac', bitrate='192k', tracks=None, artist='', album='', cover=None):
    input_filename_fullpath = os.path.join(config.server_clean_folder, input_filename)
    input_basename = os.path.basename(input_filename).split('.wav')[0]

    # Pull markers from wave file
    try:
        file_markers = read_markers(input_filename_fullpath)
    except IOError:
        errors.append(input_filename_fullpath)
        return

    ifile = wave.open(input_filename_fullpath)
    ifile_params = ifile.getparams()

    # Add start and end markers to list
    print input_filename
    if not file_markers:
        print
        print 'Waaait. Ain\'t no markers here... ({0})'.format(input_filename)
        print
    if not file_markers or file_markers[0] > 1000:
        print 'Start marker added.'
        file_markers.insert(0, 0)
    if not file_markers or file_markers[-1] < ifile.getnframes() - 1000:
        print 'End marker added.'
        file_markers.append(ifile.getnframes())
    # Remove marker near beginning/end of track (usually silent)
    if file_markers[-1] - file_markers[-2] < 400000: # ~9 seconds
        print 'Doubled end-marker deleted.'
        del file_markers[-2]
    if file_markers[1] - file_markers[0] < 200000: # ~4.5 seconds
        print 'Doubled beginning-marker deleted.'
        del file_markers[1]
    for i in range(len(file_markers) - 1):
        if file_markers[i + 1] - file_markers[i] < 88200: # 2 seconds
            print 'Doubled mid-file marker deleted.'
            del file_markers[i]
    print 'Markers:', file_markers

    # Load AudioSegment for encoded segments
    if export_format is not 'wav':
        ifile_mp3 = AudioSegment.from_wav(input_filename_fullpath)

    # Loop through cues and write regions (assumes start and end markers)
    for marker_num, marker in enumerate(file_markers):
        if marker_num == len(file_markers) - 1:
            break
        region_basename = input_basename + '_' + str(marker_num + 1).zfill(2) + '.wav'
        region_name = os.path.join(config.split_folder, region_basename)
        region_length = file_markers[marker_num + 1] - marker
        m, s = divmod(region_length / 44100, 60)
        #print 'Region {0} | {1}:{2} -> {3} ({4} - {5})'.format(marker_num, m, str(s).zfill(2), region_name, (marker / 44.1), 
        #    (file_markers[marker_num + 1] / 44.1)) #debug
        if export_format is not 'wav':
            mp3_track = ifile_mp3[(marker / 44.1):(file_markers[marker_num + 1] / 44.1)]
            if tracks:
                mp3_title = tracks[marker_num]
            else:
                mp3_title = 'Track ' + str(marker_num + 1)
            mp3_tags = {'title': mp3_title, 'artist': artist, 'albumartist': artist, 'album': album,
                        'track': (marker_num + 1)}
            mp3_fname = os.path.join(config.split_folder, (os.path.splitext(region_basename)[0] + '.' + export_format))
            # print 'Export:', mp3_fname, export_format, bitrate, mp3_tags
            mp3_track.export(out_f=mp3_fname, format=export_format, bitrate=bitrate, tags=mp3_tags)
            # Add cover art
            if cover:
                audio = MP3(mp3_fname, ID3=ID3)
                # Add ID3 tag if it doesn't exist
                try:
                    audio.add_tags()
                except error:
                    pass
                audio.tags.add(
                    APIC(
                        encoding=3,  # 3 is for utf-8
                        mime='image/jpeg',  # image/jpeg or image/png
                        type=3,  # 3 is for the cover image
                        desc=u'Cover',
                        data=open(cover, 'rb').read()
                    )
                )
                audio.save()
            else:
                pass
                #print 'No cover found for item ', mp3_fname
        else:
            region = wave.open(region_name, 'w')
            region.setparams(ifile_params)
            region.writeframes(ifile.readframes(region_length))
            region.close()
    ifile.close()


if __name__ == '__main__':
    # Make input filename list
    logging.basicConfig(level=config.log_level)

    if config.input_resplit_list:
        utils.export_csv(['re-split_list', 'resplit-track-lists'])
        with open(config.resplit_list_path, 'r') as resplit_list:
            rows = csv.reader(resplit_list)
            for row in rows:
                numeric_length = 50
                for i, c in enumerate(row[0]):
                    if not c.isdigit():
                        numeric_length = i
                        break
                #print row[0][:numeric_length].zfill(5) + row[0][numeric_length:] + '_clean.wav'
                input_filename_list.append(row[0][:numeric_length].zfill(5) + row[0][numeric_length:] + '_clean.wav')
        # Remove bad split files from Julius
        deleted_resplits = []
        for each_file in os.listdir(config.server_split_folder):
            if any(each for each in input_filename_list if each_file.split('_clean')[0].startswith(each.split('_clean')[0])):
                deleted_resplits.append(each_file)
                send2trash(os.path.join(config.server_split_folder, each_file))
        print 'Deleted re-splits from Julius ({0}): {1}'.format(len(deleted_resplits), deleted_resplits)
        print 'Input filenames (re-record list):', len(input_filename_list)
    elif config.serial_series:
        for g in os.listdir(input_path):
            if input_filename_list_range[0] <= g < input_filename_list_range[1] and g.lower().endswith('.wav'):
                input_filename_list.append(g)
                # If end of range reached (redundant?)
                if g.startswith(input_filename_list_range[1]):
                    break
        print 'Input filenames (series):', len(input_filename_list)
    elif config.input_whole_folder:
        for f in os.listdir(config.server_clean_folder):
            if f.endswith('.wav'):
                input_filename_list.append(f)
        print 'Input filenames (folder):', len(input_filename_list)
    else:
        input_filename_list = [input_filename]

    if not config.input_resplit_list:
        input_filename_list.sort()

    print input_filename_list

    # RUN THE TRAP
    pool_array = [os.path.join(config.server_clean_folder, each) for each in input_filename_list]

    '''
    if config.pool_processing:
        pool = multiprocessing.Pool(min(6, multiprocessing.cpu_count() - 1))
        pool.map(split_file, pool_array)
    else:
        for each in pool_array:
            split_file(each)
    '''

    for each in pool_array:
        split_file(each)

    if errors:
        print ' ---------------'
        print 'Files not found:'
        for error in errors:
            print error

    '''
    print 'Discogs time!'
    import discogs
    discogs.main()
    '''