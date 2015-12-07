import sys, numpy, struct, warnings, wave, os
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error
from pydub import AudioSegment


class WavFileWarning(UserWarning):
    pass

_big_endian = False

WAVE_FORMAT_PCM = 0x0001
WAVE_FORMAT_IEEE_FLOAT = 0x0003
WAVE_FORMAT_EXTENSIBLE = 0xfffe
KNOWN_WAVE_FORMATS = (WAVE_FORMAT_PCM, WAVE_FORMAT_IEEE_FLOAT)

# Input file parameters (name & location)
input_filename_series = False
input_whole_folder = False
input_filename = '00106_clean.wav'
input_filename_list_range = range(228, 229)
input_filename_list = []
input_path = 'D:\splitty'
output_path = 'D:\split'
export_format = 'mp3'

# assumes file pointer is immediately after the 'fmt ' id
def _read_fmt_chunk(fid):
    if _big_endian:
        fmt = '>'
    else:
        fmt = '<'
    res = struct.unpack(fmt+'iHHIIHH',fid.read(20))
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
    size = struct.unpack(fmt,fid.read(4))[0]

    bytes = bits//8
    if bits == 8:
        dtype = 'u1'
    else:
        if _big_endian:
            dtype = '>'
        else:
            dtype = '<'
        if comp == 1:
            dtype += 'i%d' % bytes
        else:
            dtype += 'f%d' % bytes
    if not mmap:
        data = numpy.fromstring(fid.read(size), dtype=dtype)
    else:
        start = fid.tell()
        data = numpy.memmap(fid, dtype=dtype, mode='c', offset=start, shape=(size//bytes,))
        fid.seek(start + size)

    if noc > 1:
        data = data.reshape(-1,noc)
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
    if hasattr(filename,'read'):
        fid = filename
        mmap = False
    else:
        fid = open(filename, 'rb')

    try:
        fsize = _read_riff_chunk(fid)
        noc = 1
        bits = 8
        comp = WAVE_FORMAT_PCM
        while (fid.tell() < fsize):
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
        if not hasattr(filename,'read'):
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
    if hasattr(filename,'write'):
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
        sbytes = rate*(bits // 8)*noc
        ba = noc * (bits // 8)
        fid.write(struct.pack('<ihHIIHH', 16, comp, noc, rate, sbytes, ba, bits))
        # data chunk
        fid.write(b'data')
        fid.write(struct.pack('<i', data.nbytes))
        if data.dtype.byteorder == '>' or (data.dtype.byteorder == '=' and sys.byteorder == 'big'):
            data = data.byteswap()
        _array_tofile(fid, data)

        # Determine file size and place it in correct position at start of the file.
        size = fid.tell()
        fid.seek(4)
        fid.write(struct.pack('<i', size-8))

    finally:
        if not hasattr(filename,'write'):
            fid.close()
        else:
            fid.seek(0)


if sys.version_info[0] >= 3:
    def _array_tofile(fid, data):
        # ravel gives a c-contiguous buffer
        fid.write(data.ravel().view('b').data)
else:
    def _array_tofile(fid, data):
        fid.write(data.tostring())

def read_markers(f, mmap=False):
    if hasattr(f,'read'):
        fid = f
    else:
        fid = open(f, 'rb')
    fsize = _read_riff_chunk(fid)
    cues = []
    while (fid.tell() < fsize):
        chunk_id = fid.read(4)
        #print chunk_id
        if chunk_id == b'cue ':
            size, numcue = struct.unpack('<ii',fid.read(8))
            for c in range(numcue):
                id, position, datachunkid, chunkstart, blockstart, sampleoffset = struct.unpack('<iiiiii',fid.read(24))
                if sampleoffset not in cues:
                    cues.append(sampleoffset)
        else:
            _skip_unknown_chunk(fid)    
    fid.close()
    return cues

def split_file(input_filename, export_format='wav', bitrate='192', tracks=None, artist='Unknown', album='Untitled', cover=None):
    input_filename = input_filename.split('.wav')[0]
    file_markers = read_markers(input_filename_fullpath)
    print 'Markers:', file_markers

    print 'BLOOOAAARRRRGHHGGGGHHHHH!!! (Please hold...)'
    ifile = wave.open(input_filename_fullpath)
    ifile_params = ifile.getparams()

    # Add start and end markers to list
    if file_markers[0] > 1000:
        print 'Start marker added.'
        file_markers.insert(0, 0)
    if ifile.getnframes() - file_markers[-1] > 1000:
        print 'End marker added.'
        file_markers.append(ifile.getnframes())
    print 'New marker list:', file_markers

    # Load AudioSegment for encoded segments
    if export_format is not 'wav':
    	ifile_mp3 = AudioSegment.from_wav(input_filename_fullpath)

    # Loop through cues and write regions (assumes start and end markers)
    for marker_num, marker in enumerate(file_markers):
        #print 'Cue', marker_num, '@', marker
        if marker_num == len(file_markers) - 1:
            break
        region_name = os.path.join(output_path, input_filename)+'_'+str(marker_num + 1).zfill(2)+'.wav'
        region_length = file_markers[marker_num + 1] - marker
        print 'Region', marker_num, '@', region_length/44100.0, '->', region_name
        if export_format is not 'wav':
            print str(export_format) + ' ' + str(marker_num + 1) + ' - ' + str((marker / 44100)) + ' : ' + str((file_markers[marker_num+1] / 44100))
            mp3_track = ifile_mp3[(marker / 44.1):(file_markers[marker_num+1] / 44.1)]
            if tracks:
                mp3_title = tracks[marker_num + 1]
            else:
                mp3_title = 'Track ' + str((marker_num + 1))
            mp3_tags = {'title':mp3_title, 'artist':artist, 'album':album}
            mp3_fname = os.path.splitext(region_name)[0] + '.mp3'
            print 'Export:', mp3_fname, export_format, bitrate, mp3_tags
            mp3_track.export(out_f=mp3_fname, format=export_format, bitrate=bitrate, tags=mp3_tags)
            # Add cover art
            if cover:
                audio = MP3((os.splitext(region_name)[0] + '.mp3'), ID3=ID3)
                # Add ID3 tag if it doesn't exist
                try:
                    audio.add_tags()
                except error:
                    pass
                audio.tags.add(
                    APIC(
                        encoding=3, # 3 is for utf-8
                        mime='image/jpg', # image/jpeg or image/png
                        type=3, # 3 is for the cover image
                        desc=u'Cover',
                        data=open(cover).read()
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
        input_filename_fullpath = os.path.join(input_path, each)
        print each
        split_file(each, export_format=export_format)