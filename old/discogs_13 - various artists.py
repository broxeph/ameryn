# Ameryn Media metadata processor
# Alex Ball, 2015

import csv
import os
import time
import math
import logging
import webbrowser
import time
from ConfigParser import ConfigParser
import sys
import itertools

import discogs_client
from mutagen.flac import FLAC

import utils

CONFIG_LOCATION = 'ameryn.ini'
CLIENT_NAME = 'AmerynDiscogsBot/0.1'
CONSUMER_KEY = 'lysCMszUmXHGNcFDVmbH'
CONSUMER_SECRET = 'njuRMMqVtcCkojDvRtGhOFqstZfHBFrf'
TOKEN = u'DpladtVtvbpotOOuCMsqlPemAwdFSZgERbDFFYUI'
SECRET = u'ZFryZTlEeqoqQdwTUhQLaViZGUPPOnsKCmLvXPpe'
DISCOGS_MANUAL_AUTH = False

def main(input_resplit_list=False):
    def add_serial_metadata(input_filename):
        def discogs_auth():
            authorize_token = None
            while not authorize_token:
                discogs = discogs_client.Client(CLIENT_NAME)
                discogs.set_consumer_key(CONSUMER_KEY, CONSUMER_SECRET)
                authorize_url = discogs.get_authorize_url()
                webbrowser.open(authorize_url[2])
                authorize_token = raw_input('Enter authorize token (Or q to quit): ')
            if authorize_token.lower() == 'q': return 'q'
            access_token = discogs.get_access_token(authorize_token)
            logging.debug('access_token: {0}'.format(access_token))
            return discogs

        def average(x):
            assert len(x) > 0
            return float(sum(x)) / len(x)

        def pearson_def(x, y):
            """
            Correlation between listed Discogs release durations and split FLAC file durations.
            Would divide by zero if all durations are equal for x or y; set to return 1 instead.
            """
            assert len(x) == len(y)
            n = len(x)
            assert n > 0
            if n == 2: # Pearson's is useless for n < 3
                return (min(x[0], y[0]) / float(max(x[0], y[0]))) * (min(x[1], y[1]) / float(max(x[1], y[1])))
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
            return 1 if xdiff2 == 0 or xdiff2 == 0 else diffprod / math.sqrt(xdiff2 * ydiff2)

        def to_seconds(time_str_input):
            to_seconds_output = []
            if type(time_str_input) is list:
                for i in time_str_input:
                    i_split = i.split(':')
                    to_seconds_output.append(int(i_split[0] or 0)*60 + int(i_split[1]))
                return to_seconds_output
            elif type(time_str_input) is str or unicode:
                if ':' not in time_str_input:
                    return int(time_str_input)
                i_split = time_str_input.split(':')
                return int(i_split[0] or 0)*60 + int(i_split[1])
            elif type(time_str_input) is int:
                return time_str_input
            else:
                raise Exception('Invalid to_seconds input type: {0}'.format(type(time_str_input)))

        def boxes_pull(input_filename):
            # Pull artist, album info from boxes csv
            double_type = None
            input_filename = input_filename.lstrip('0')
            input_filename = input_filename.rsplit('-')[0]
            with open(boxes_path, 'r') as boxes:
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

        filename_matches = []
        log_comment = ''
        artist = ''
        album = ''
        track_lengths_correlation = 0
        discogs_match = False
        resplit_serial = False
        requested_serial = False

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
                if not input_resplit_list:
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

        discogs_search = True
        if input_resplit_list:        
            # Check re-split_list.csv for specified Discogs release ID
            with open(resplit_list_path, 'r') as resplit_list:
                rowdata = [row for row in csv.reader(resplit_list)]
                for row in rowdata:
                    row_serial = row[0].translate(None,' ').lower()
                    if row_serial.startswith(input_filename.lstrip('0')):
                        if 'csv' in row[1].lower():
                            print 'Skipped: track titles in resplit-track-lists.csv'                  
                            return input_filename, artist, album, track_lengths_correlation, log_comment, discogs_match
                        elif row[1].isdigit():
                            print 'Requested serial from resplit list: {0}'.format(row[1])
                            resplit_serial = True
                            output = [discogs.release(int(row[1]))]
                            discogs_search = False
                            break
                        elif row[1]:
                            print 'Re-split serial field non-numeric!'
        if discogs_search:
            query = ''.join(ch for ch in (artist+' '+album) if ch.isalnum() or ch in ' -/,\'')
            # Search Discogs for release ID/artist + album
            output = discogs.search(query, type='release')
            print 'Discogs results for "{0}":'.format(query)

        # Print track listing, tag FLAC files with titles
        accept_blank_tracklist_durations = False
        for search_loop in range(2):
            if accept_blank_tracklist_durations and requested_serial:
                output = discogs.search(query, type='release')
            time.sleep(discogs_request_interval) # Wait to comply with Discogs 60 requests/minute limit
            try:
                for i, result in enumerate(output):
                    if i >= max_search_tries:
                        accept_blank_tracklist_durations = True
                        print 'No results with track times found! Let\'s get a bit fuzzier...'
                        break
                    time.sleep(discogs_request_interval) # Wait to comply with Discogs 60 requests/minute limit
                    if hasattr(result, 'tracklist'): #and type(result) != discogs_client.Master:
                        if resplit_serial or accept_blank_tracklist_durations:
                            tracklist = [track for track in result.tracklist]
                        else:
                            tracklist = [track for track in result.tracklist if track.duration and to_seconds(track.duration) > 0]
                        if not tracklist:
                            print 'Result {0}: No tracks found. Continuing...'.format(str(i + 1))
                            continue
                        elif len(tracklist) != len(result.tracklist):
                            print 'Result {0}: Some tracks missing durations. Be careful!'.format(str(i + 1))
                        elif len(tracklist) == len(filename_matches):
                            print '----------------------'
                            print 'Result', str(i + 1)
                            print 'Release ID:', result.data['id']
                            print 'Artist:', result.artists[0].name.encode('utf-8')
                            print 'Album:', result.title.encode('utf-8')

                            # Funky double handling
                            if double_type in ['1/4', '1/3'] and filename_matches[0][-7] not in 'abcd':
                                if not result.tracklist[0].position:
                                    print 'Result {0}: Nope! (No position info found in Discogs)'.format(str(i + 1))
                                    continue
                                if not result.tracklist[0].position[0].isalpha():
                                    print 'Result {0}: Nope! (No side info in Discogs positions)'.format(str(i + 1))
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

                            if tracklist[0].duration and not resplit_serial:
                                # Check correlation of Discogs track lengths with those of FLAC files
                                discogs_lengths = [track.duration for track in tracklist if track.duration]
                                flac_lengths = []
                                for match in filename_matches:
                                    audio = FLAC(os.path.join(flac_directory, match))
                                    flac_length = time.strftime('%M:%S', time.gmtime(audio.info.length)).lstrip('0')
                                    flac_lengths.append(flac_length)
                                track_lengths_correlation = round(pearson_def(to_seconds(discogs_lengths), to_seconds(flac_lengths)),4)
                                print 'Track lengths correlation:', track_lengths_correlation
                                if track_lengths_correlation < min_correlation:
                                    print 'Result {0}: Low correlation. Best check yoself!'.format(str(i + 1))
                                    continue

                            # Write tags to FLAC files
                            discogs_match = True
                            for track, match in zip(tracklist, filename_matches):
                                audio = FLAC(os.path.join(flac_directory, match))
                                audio['tracknumber'] = track.position
                                audio['title'] = track.title
                                if 'artists' in track.data:
                                    # Add artist info to compilation album tracks
                                    audio['artist'] = track.data['artists'][0]['name'].split('(')[0].strip()
                                flac_length = time.strftime('%M:%S', time.gmtime(audio.info.length)).lstrip('0')
                                print track.position, track.title.encode('utf-8'), track.duration, '-->', match, flac_length
                                audio.save()
                            return input_filename, artist, album, track_lengths_correlation, log_comment, discogs_match
                        else:
                            print 'Result '+str(i + 1)+': Nope! ('+str(len(tracklist))+' != '+str(len(filename_matches))+')'
                else:
                    if len(output) == 0: # Don't retry fuzzy-style if there weren't any Discogs query matches
                        log_comment = 'No matches for Discogs query!'
                        return input_filename, artist, album, track_lengths_correlation, log_comment, discogs_match
                    elif search_loop == 0:
                        accept_blank_tracklist_durations = True
                        print 'No results with track times found! Let\'s get a bit fuzzier...'
            except Exception as e: # httplib.BadStatusLine?
                print 'httplib.BadStatusLine (?) error:', e
                return None
        else:
            log_comment = 'No proper Discogs matches! Dork.'
        return input_filename, artist, album, track_lengths_correlation, log_comment, discogs_match

    # Initial variables
    config = ConfigParser()
    config.read(CONFIG_LOCATION)

    input_filename_series = config.getboolean('discogs', 'input_filename_series')
    input_whole_folder = config.getboolean('discogs', 'input_whole_folder')
    use_boxes_csv = config.getboolean('discogs', 'use_boxes_csv')
    input_filenames = config.get('discogs', 'input_filenames')
    input_filename_list_start = config.getint('discogs', 'input_filename_list_start')
    input_filename_list_end = config.getint('discogs', 'input_filename_list_end')
    flac_directory = config.get('discogs', 'flac_directory')
    boxes_path = config.get('general', 'boxes_path')
    log_to_file = config.getboolean('discogs', 'log_to_file')
    log_path = config.get('general', 'log_path')
    discogs_request_interval = config.getfloat('discogs', 'discogs_request_interval') # seconds between API requests
    resplit_list_path = config.get('general', 'resplit_list_path')
    min_correlation = config.getfloat('discogs', 'min_correlation')
    max_search_tries = config.getint('discogs', 'max_search_tries')
    max_error_tries = config.getint('discogs', 'max_error_tries')
    resplit_track_lists_path = config.get('general', 'resplit_track_lists_path')
    input_resplit_list = config.getboolean('split', 'input_resplit_list')
    server_split_path = config.get('general', 'server_split_path')

    input_filename_list_range = range(input_filename_list_start, input_filename_list_end)
    input_filename_list = []
    matches_count = 0
    start_time = time.time()
    discogs_logged_in = False
    tries = 0
    runtime_errors = []

    # Logging setup
    if log_to_file:
        logging.basicConfig(filename=os.path.join(log_path, 'log.csv'), format='%(levelname)s,%(message)s', level=logging.INFO)
    else:
        logging.basicConfig(format='%(levelname)s,%(message)s', level=logging.DEBUG)

    # Log into Discogs
    if not DISCOGS_MANUAL_AUTH:
        discogs = discogs_client.Client(CLIENT_NAME, CONSUMER_KEY, CONSUMER_SECRET, TOKEN, SECRET)
    else:
        while not discogs_logged_in:
            try:
                discogs = discogs_auth()
                if discogs == 'q': sys.exit()
                discogs_logged_in = True
            except:
                print 'Nope! Try again.'

    # Collect, print input filenames
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
    elif type(input_filenames) is not list:
        input_filename_list = input_filenames.split(',')
    else:
        input_filename_list = input_filenames
    files_count = len(input_filename_list)

    # Grab spreadsheet from Google Drive
    utils.export_csv('Boxes!')

    # Do the things
    while tries == 0 or runtime_errors and tries <= max_error_tries:
        if runtime_errors:
            print 'Runtime errors:', runtime_errors
            print '{0} runtime errors found! See above.'.format(len(runtime_errors))
            input_filename_list = runtime_errors
            runtime_errors = []
        for each in input_filename_list:
            result = add_serial_metadata(each)
            if result is None:
                log_comment = 'We tried. We httplib.BadStatusLined.'
                runtime_errors.append(each)
            else:
                input_filename, artist, album, track_lengths_correlation, log_comment, discogs_match = result
                if discogs_match:
                    matches_count += 1
            if result or tries > 3:
                # Log track data
                print log_comment
                artist = artist.translate(None, ',') if artist else ''
                album = album.translate(None, ',') if album else ''
                logging.info('%s,%s,%s,%s,%s', input_filename, artist, album, track_lengths_correlation, log_comment)
        tries += 1

    # Now the items with manually-named track titles from resplit_track_lists.csv
    if input_resplit_list:
        with open(resplit_track_lists_path, 'r') as resplit_track_lists:
            flac_directory_list = os.listdir(flac_directory)
            server_directory_list = os.listdir(server_split_path)
            rowdata = [row for row in csv.reader(resplit_track_lists)]
            for row in rowdata:
                query = [''.join(x) for _, x in itertools.groupby(row[0], key=str.isdigit)]
                query = ''.join([query[0].zfill(5)] + query[1:])
                # Check for filename query matches
                filename_matches = [os.path.join(flac_directory, each) for each in flac_directory_list if each.startswith(query)]
                if not filename_matches:
                    filename_matches = [os.path.join(server_split_path, each) for each in server_directory_list if each.startswith(query)]
                if not filename_matches:
                    print 'No split (_xx) audio file matches for resplit serial {0}! Dork.'.format(row[0])
                    continue
                # Write tags to FLAC files
                tracklist = [col for col in row[1:] if col]
                for position, (track, match) in enumerate(zip(tracklist, filename_matches), 1):
                    audio = FLAC(os.path.join(flac_directory, match))
                    audio['tracknumber'] = str(position)
                    audio['title'] = track.decode('unicode-escape')
                    flac_length = time.strftime('%M:%S', time.gmtime(audio.info.length)).lstrip('0')
                    print position, flac_length, track, '-->', match
                    audio.save()
                matches_count += 1

    # Done? Great!
    accuracy = int(round(matches_count / float(files_count) * 100))
    processing_time = int(round(time.time() - start_time))
    print 'Great success! {0} files ({1} matches, {2}%) processed in {3}s.'.format(files_count, matches_count, accuracy, processing_time)

# RUN THE TRAP
if __name__ == '__main__':
    main()