# Ameryn Media metadata processor
# Alex Ball, 2015

import discogs_client
from mutagen.flac import FLAC
import csv, os, time, math, logging
import webbrowser
import time

# Initial variables
input_filename_series = False
input_whole_folder = True
use_boxes_csv = True
input_filename = '00228'
input_filename_list = []
input_filename_list_range = range(1, 5)
flac_directory = 'D:/split'
csv_name = 'boxes.csv'
LOG_TO_FILE = True
CLIENT_NAME = 'AmerynDiscogsBot/0.1'
CONSUMER_KEY = 'lysCMszUmXHGNcFDVmbH'
CONSUMER_SECRET = 'njuRMMqVtcCkojDvRtGhOFqstZfHBFrf'
LOG_PATH = 'D:/temp/'
DISCOGS_REQUEST_INTERVAL = 2 # seconds between API requests
matches_count = 0

def discogs_auth():
    discogs = discogs_client.Client(CLIENT_NAME)
    discogs.set_consumer_key(CONSUMER_KEY, CONSUMER_SECRET)
    authorize_url = discogs.get_authorize_url()
    webbrowser.open(authorize_url[2])
    authorize_token = raw_input('Enter authorize token: ')
    access_token = discogs.get_access_token(authorize_token)
    logging.debug('access_token: {0}'.format(access_token))
    return discogs

def average(x):
    assert len(x) > 0
    return float(sum(x)) / len(x)

def pearson_def(x, y):
    assert len(x) == len(y)
    n = len(x)
    assert n > 0
    avg_x = average(x)
    avg_y = average(y)
    diffprod = 0
    xdiff2 = 0
    ydiff2 = 0
    for idx in range(n):
        xdiff = x[idx] - avg_x
        ydiff = y[idx] - avg_y
        diffprod += xdiff * ydiff
        xdiff2 += xdiff * xdiff
        ydiff2 += ydiff * ydiff
    return diffprod / math.sqrt(xdiff2 * ydiff2)

def to_seconds(time_str_list):
    to_seconds_output = []
    for i in time_str_list:
        i_split = i.split(':')
        to_seconds_output.append(int(i_split[0] or 0)*60 + int(i_split[1]))
    return to_seconds_output

def boxes_pull(input_filename):
    # Pull artist, album info from boxes csv
    double_type = None
    input_filename = input_filename.lstrip('0')
    input_filename = input_filename.rsplit('-')[0]
    with open(csv_name, 'r') as boxes:
        spamreader = csv.reader(boxes)
        rowdata = []
        for row in spamreader:
            rowdata.append(row)
        for row in rowdata:
            row_serial = row[0].translate(None,' ').lower()
            if row_serial == input_filename:
                print 'Match!'
                print 'RealRow:', row
                artist = row[1]
                album = row[2]
                if album.lower() == 'self titled' or album.lower() == 'self-titled':
                    album = artist
                if row[5].lower() == 'x':
                    print 'Double trouble!'
                    if row[6].startswith('1/2') or row[6] == '':
                        print '1/2!'
                        double_type = '1/2'
                    elif row[6].startswith('1/4'):
                        print 'Eeeek! 1/4!!'
                        double_type = '1/4'
                elif row[5].lower() and row[5].lower() != 'x':
                    double_type = 'other'
                if 'live' in row[4].lower():
                    print 'Eeeek! Live album!'
                return artist, album, double_type
        else:
            return None, None, None

def add_serial_metadata(input_filename):
    filename_matches = []
    log_comment = ''
    artist = ''
    album = ''
    track_lengths_correlation = 0
    discogs_match = False

    print
    print '----------------------'
    print 'Query:', input_filename

    # Check for filename query matches
    for each_file in os.listdir(flac_directory):
        if each_file.startswith(input_filename):
            # Skip 'a' matches for non-'a' files
            if len(input_filename) == 5 and each_file[5] != '_':
                continue            
            filename_matches.append(each_file)
    if not filename_matches:
        print 'No split (_xx) audio file matches! Dork.'
        return input_filename, artist, album, track_lengths_correlation, log_comment, discogs_match
    
    # Check for artist tags, add from spreadsheet if enabled and necessary
    if use_boxes_csv:
        artist, album, double_type = boxes_pull(input_filename)
        if (artist, album) == (None, None):
            log_comment = 'No spreadsheet match found.'
            return input_filename, artist, album, track_lengths_correlation, log_comment, discogs_match
        elif double_type == 'other':
            log_comment = 'Freaky double! Engage manual tagging mode.'
            return input_filename, artist, album, track_lengths_correlation, log_comment, discogs_match
        # Add tracknumber, album, artist to FLAC files
        for each_file in filename_matches:
            audio = FLAC(os.path.join(flac_directory, each_file))
            audio['artist'] = artist
            audio['album'] = album
            audio.save()
    else:
        try:
            artist = FLAC(os.path.join(flac_directory, filename_matches[0]))['artist'][0]
            album = FLAC(os.path.join(flac_directory, filename_matches[0]))['album'][0]
            print 'Metadata found. Artist:', artist, 'Album:', album
        except:
            print 'No artist/album tags; boxes spreadsheet not searched:', input_filename
            return input_filename, artist, album, track_lengths_correlation, log_comment

    # Search Discogs for artist and album
    query = artist+' '+album
    for char in '!@#$.?/;:&\'"':
        query = query.replace(char,' ')
    output = discogs.search(query)
    print 'Discogs results for "'+query+'":', len(output)

    # Print track listing, tag FLAC files with titles
    for i, result in enumerate(output):        
        time.sleep(DISCOGS_REQUEST_INTERVAL) # Wait to comply with Discogs 60 requests/minute limit
        if hasattr(result,'tracklist') and type(result) != discogs_client.Master:
            tracklist = [track for track in result.tracklist if track.duration]
            if not tracklist:
                print 'Result {0}: No track lengths found. Continuing...'.format(str(i + 1))
                continue
            elif len(tracklist) != len(result.tracklist):
                print 'Some tracks missing durations. Be careful!'
            elif len(tracklist) == len(filename_matches):
                print '----------------------'
                print 'Result', str(i + 1)
                print 'Release ID:', result.data['id']
                print 'Artist:', result.artists[0].name.encode('utf-8')
                print 'Album:', result.title.encode('utf-8')

                # Funky double handling
                if double_type in ['1/4', '1/3'] and filename_matches[0][-7] not in 'abcd':
                    if not result.tracklist[0].position:
                        print 'Result '+str(i + 1)+': Nope! (No position info found in Discogs)'
                        continue
                    if double_type == '1/4':
                        sort_key = ['a', 'd', 'b', 'c']
                    if double_type == '1/3':
                        sort_key = ['a', 'c', 'b', 'd']
                    # Reorder tracklist by alpha position key
                    tracklist_sorted = []
                    for key in sort_key:
                        for track in tracklist:
                            if track.position.lower().startswith(key):
                                tracklist_sorted.append(track)
                    tracklist = tracklist_sorted

                # Check correlation of Discogs track lengths with those of FLAC files
                discogs_lengths = [track.duration for track in tracklist if track.duration]
                flac_lengths = []
                for match in filename_matches:
                    audio = FLAC(os.path.join(flac_directory, match))
                    flac_length = time.strftime('%M:%S', time.gmtime(audio.info.length)).lstrip('0')
                    flac_lengths.append(flac_length)
                track_lengths_correlation = round(pearson_def(to_seconds(discogs_lengths), to_seconds(flac_lengths)),4)
                print 'Track lengths correlation:', track_lengths_correlation
                if track_lengths_correlation < 0.80:
                    log_comment = '----- Low correlation. Best check yoself!'
                    continue

                # Write tags to FLAC files
                discogs_match += 1                
                for track, match in zip(tracklist, filename_matches):
                    audio = FLAC(os.path.join(flac_directory, match))
                    audio['tracknumber'] = track.position
                    audio['title'] = track.title
                    flac_length = time.strftime('%M:%S', time.gmtime(audio.info.length)).lstrip('0')
                    print track.position, track.title.encode('utf-8'), track.duration, '-->', match, flac_length
                    audio.save()
                return input_filename, artist, album, track_lengths_correlation, log_comment, discogs_match
            else:
                print 'Result '+str(i + 1)+': Nope! ('+str(len(tracklist))+' != '+str(len(filename_matches))+')'
        elif i > 40:
            log_comment = 'Okay that\'s enough Spot. Heel!'
            break
    else:
        log_comment = 'No Discogs matches! Dork.'
    return input_filename, artist, album, track_lengths_correlation, log_comment, discogs_match

# RUN THE TRAP
if __name__ == '__main__':
    start_time = time.time()
    if LOG_TO_FILE:
        logging.basicConfig(filename=os.path.join(LOG_PATH, 'log.csv'), format='%(levelname)s,%(message)s', level=logging.INFO)
    else:
        logging.basicConfig(format='%(levelname)s,%(message)s', level=logging.DEBUG)
    discogs = discogs_auth()

    if input_filename_series:
        for f in input_filename_list_range:
            input_filename_list.append(str(f).zfill(5))
        print 'Input filenames (series):', input_filename_list

    elif input_whole_folder:
        for f in os.listdir(flac_directory):
            if f.endswith('.flac') or f.endswith('.mp3'):
                f = f.rsplit('_clean')[0]
                if f[-2] == '-':
                    f = f[:-1]
                if f not in input_filename_list:
                    input_filename_list.append(f)
        print 'Input filenames ('+flac_directory+'):', input_filename_list

    else:
        input_filename_list = [input_filename]

    for each in input_filename_list:
        input_filename, artist, album, track_lengths_correlation, log_comment, discogs_match = add_serial_metadata(each)
        if discogs_match: matches_count += 1
        # Log track data
        print log_comment
        artist = artist.translate(None, ',')
        album = album.translate(None, ',')
        logging.info('%s,%s,%s,%s,%s', input_filename, artist, album, track_lengths_correlation, log_comment)

    print 'Great success! {0} files ({1} matches) processed in {2}s.'.format(len(input_filename_list), matches_count, round(time.time() - start_time, 1))