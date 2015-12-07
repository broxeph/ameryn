# Crystal Record Transfers metadata processor
# Alex Ball, 2014

import discogs_client as discogs
import csv
import os
from mutagen.flac import FLAC
import time
import math

# Initial variables
discogs.user_agent = 'CrystalDiscogsBot/0.1 +http://www.crystal-lp.com'
input_serial = '00095'
#query = 'john, elton friends'
#query_tracks = 9
discogs_lengths = []
flac_lengths = []

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

def add_serial_metadata(query_serial):
	tracks_count = 0
	query_matches = []

	# Pull artist, album info from boxes csv
	with open('boxes.csv', 'r') as boxes:
		spamreader = csv.reader(boxes)
		rowdata = []
		for row in spamreader:
			rowdata.append(row)
		for row in rowdata:
			row_serial_nospaces = row[0].translate(None,' ').lower()
			query_serial_nozeroes = query_serial.lstrip('0')
			if row_serial_nospaces == query_serial_nozeroes:
				print 'Match!'
				print 'RealRow:',row
				artist = row[1]
				album = row[2]
				query = row[1]+' '+row[2]
				if row[6] == '1/4':
					print 'Eeeek! 1/4!!'
					return
				break
		else:
			print 'No spreadsheet match found for album #'+query_serial+'.'
			return
		print
		print 'query_serial:', query_serial
		print 'row_serial_nospaces:', row_serial_nospaces
		print 'query_serial_nozeroes:', query_serial_nozeroes
		#'''
		# Count tracks, add tracknumber, album, artist to FLAC files
		print '----------------------'
		print 'Query serial:', query_serial
		print 'Current directory:', os.getcwd()
		for each_file in os.listdir('.'):
			if each_file[-7] == '.':
				each_file_newname = each_file[:12]+'0'+each_file[12:]
				os.rename(each_file, each_file_newname)
		for each_file in os.listdir('.'):
			if each_file.startswith(query_serial):
				print each_file
				tracks_count += 1
				query_matches.append(each_file)
				audio = FLAC(each_file)
				audio['tracknumber'] = str(tracks_count)
				audio['artist'] = artist
				audio['album'] = album
				audio.save()
		if tracks_count == 0:
			print 'No audio file matches! Dork.'
			return
		print 'Tracks in #'+query_serial+':', tracks_count

		# Search Discogs for given query
		query = query.translate(None, '?.!/;:')
		output = discogs.Search(query).results()
		print 'Discogs results for "'+query+'":', output
		print 'Number of results:', len(output)

		# Print track listing, tag FLAC files with titles
		for result in output:
			if hasattr(result,'tracklist'):
				if len(result.tracklist) == tracks_count:
					print '----------------------'
					print result.artists, result.title
					for track, match in zip(result.tracklist, query_matches):
						audio = FLAC(match)
						audio['title'] = track['title']
						flac_length = time.strftime('%M:%S', time.gmtime(audio.info.length)).lstrip('0')
						print track['title'], track['duration'], '-->', match, flac_length
						audio.save()
						if track['duration']:
							discogs_lengths.append(track['duration'])
						flac_lengths.append(flac_length)
					if len(discogs_lengths) > 0:
						track_lengths_correlation = round(pearson_def(to_seconds(discogs_lengths), to_seconds(flac_lengths)),4)
						print 'Track lengths correlation: ', track_lengths_correlation
						if track_lengths_correlation < 0.95:
							print '- - - Low correlation. Best check yoself!'
					else:
						print 'No track lengths found on Discogs. Oh well.'
					return
				else:
					print 'Nope!'
		print 'No Discogs matches! Dork.'
#'''

add_serial_metadata(input_serial)