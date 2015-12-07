# Crystal Record Transfers metadata processor
# Alex Ball, 2014

import discogs_client as discogs
from mutagen.flac import FLAC
import csv, os, time, math, logging

# Initial variables
discogs.user_agent = 'CrystalDiscogsBot/0.1 +http://www.crystal-lp.com'
input_filename_series = False
input_whole_folder = True
use_boxes_csv = True
input_filename = '00458'
input_filename_list = []
input_filename_list_range = range(1, 5)
flac_directory = 'c:/temp/taggy temp/'
csv_name = 'boxes.csv'
logging.basicConfig(filename=flac_directory+'log.csv', format='%(levelname)s,%(message)s', level=logging.INFO)

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
		to_seconds_output.append(int(i_split[0])*60 + int(i_split[1]))
	return to_seconds_output

def boxes_pull(input_filename):
	# Pull artist, album info from boxes csv
	input_filename_nozeroes = input_filename.lstrip('0')
	with open(csv_name, 'r') as boxes:
		spamreader = csv.reader(boxes)
		rowdata = []
		for row in spamreader:
			rowdata.append(row)
		for row in rowdata:
			row_serial_nospaces = row[0].translate(None,' ').lower()
			if row_serial_nospaces == input_filename_nozeroes:
				print 'Match!'
				print 'RealRow:',row
				artist = row[1]
				album = row[2]
				if album.lower() == 'self titled' or album.lower() == 'self-titled':
					album = artist
				if row[5]:
					print 'Double trouble!'
				if row[6].startswith('1/4'):
					print 'Eeeek! 1/4!!'
				if row[6].startswith('1/3'):
					print 'No way! 1/3!!!'
				if 'live' in row[4].lower():
					print 'Eeeek! Live album!'
				return artist, album
		else:
			return None, None

def add_serial_metadata(input_filename):
	tracks_count = 0
	filename_matches = []
	discogs_lengths = []
	flac_lengths = []
	logging.disable(logging.INFO)

	print '----------------------'
	print 'Query:', input_filename

	# Check for clean filename query matches
	for each_file in os.listdir(flac_directory):
		if each_file.startswith(input_filename+'_clean'):
			filename_matches.append(each_file)
	tracks_count = len(filename_matches)
	if not filename_matches:
		print 'No split (_xx) audio file matches! Dork.'
		return
	
	# Check for artist tags, add from spreadsheet if enabled and necessary
	try:
		artist = FLAC(os.path.join(flac_directory, filename_matches[0]))['artist'][0]
		album = FLAC(os.path.join(flac_directory, filename_matches[0]))['album'][0]
		print 'Metadata found. Artist:', artist, 'Album:', album
	except:
		if not use_boxes_csv:
			print 'No artist/album tags; boxes spreadsheet not searched:', input_filename
			return
		else:
			artist, album = boxes_pull(input_filename)
			if (artist, album) == (None, None):
				print 'No spreadsheet match found for album:', input_filename
				return
			else:
				# Add tracknumber, album, artist to FLAC files
				for each_file in filename_matches:
					audio = FLAC(os.path.join(flac_directory, each_file))
					audio['artist'] = artist
					audio['album'] = album
					audio.save()

	# Search Discogs for artist and album
	query = artist+' '+album
	for char in '!@#$.?/;:&':
		query = query.replace(char,'')
	output = discogs.Search(query).results()
	print 'Discogs results for "'+query+'":', len(output)

	# Print track listing, tag FLAC files with titles
	for i, result in enumerate(output):
		if hasattr(result,'tracklist'):
			if len(result.tracklist) == tracks_count:
				print 'Result '+str(i + 1)+': Yup!'
				print '----------------------'
				print 'Release ID:', result.data['id']
				print 'Artist:', result.artists[0].name.encode('utf-8')
				print 'Album:', result.title.encode('utf-8')
				print 'filename_matches:', filename_matches
				for track, match in zip(result.tracklist, filename_matches):
					audio = FLAC(os.path.join(flac_directory, match))
					audio['tracknumber'] = track['position']
					audio['title'] = track['title']
					flac_length = time.strftime('%M:%S', time.gmtime(audio.info.length)).lstrip('0')
					print track['position'], track['title'], track['duration'], '-->', match, flac_length
					audio.save()
					if track['duration']:
						discogs_lengths.append(track['duration'])
					flac_lengths.append(flac_length)

				#Check correlation of Discogs track lengths with those of FLAC files
				if len(discogs_lengths) > 0:
					track_lengths_correlation = round(pearson_def(to_seconds(discogs_lengths), to_seconds(flac_lengths)),4)
					log_comment = track_lengths_correlation
					print 'Track lengths correlation: ', track_lengths_correlation
					if track_lengths_correlation < 0.95:
						print '- - - Low correlation. Best check yoself!'
				else:
					log_comment = 'No track lengths found on Discogs. Oh well.'
				
				# Log track data
				logging.disable(logging.NOTSET)
				logging.info('%s,%s,%s,%s', input_filename, artist, album, log_comment)
				break
			else:
				print 'Result '+str(i + 1)+': Nope! ('+str(len(result.tracklist))+' != '+str(tracks_count)+')'
	else:
		log_comment = 'No Discogs matches! Dork.'
		logging.disable(logging.NOTSET)
		logging.info('%s,,,%s', input_filename, log_comment)


# RUN THE TRAP
if input_filename_series:
	for f in input_filename_list_range:
		input_filename_list.append(str(f).zfill(5))
	print 'Input filenames (series):', input_filename_list

elif input_whole_folder:
	for f in os.listdir(flac_directory):
		if use_boxes_csv:
			if f[5] == '_':
				f = f[:5]
			elif f[5] == ' ':
				del f[5]
			else:
				f = f[:6]
		if f not in input_filename_list:
			input_filename_list.append(f)
	print 'Input filenames (folder):', input_filename_list

else:
    input_filename_list = [input_filename]

for each in input_filename_list:
	add_serial_metadata(each)