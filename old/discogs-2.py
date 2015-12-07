# Crystal Record Transfers metadata processor
# Alex Ball, 2014

import discogs_client as discogs
import csv
import os
from mutagen.flac import FLAC

# Initial variables
discogs.user_agent = 'CrystalDiscogsBot/0.1 +http://www.crystal-lp.com'
#query = 'john, elton friends'
#query_tracks = 9
input_serial = 2

def add_serial_metadata(query_serial):
	query_serial_5digit = str(query_serial).zfill(5)
	tracks_count = 0
	query_matches = []

	# Pull artist, album info from boxes csv
	with open('boxes.csv', 'r') as boxes:
		spamreader = csv.reader(boxes)
		rowdata = []
		for row in spamreader:
			rowdata.append(row)
		for row in rowdata:
			if row[0] == str(query_serial):
				print 'Match!'
				print 'RealRow:',row
				artist = row[1]
				album = row[2]
				query = row[1]+' '+row[2]
				query = query.translate(None, '?.!/;:')
				break
		else:
			print 'No spreadsheet match found for album #'+query_serial_5digit+'.'
			print 'query_serial:', query_serial
			print 'query_serial_5digit:', query_serial_5digit
			print rowdata[1]
			return
		print

		# Count tracks, add tracknumber, album, artist to FLAC files
		print '----------------------'
		print 'Query serial:', query_serial_5digit
		print 'Current directory:', os.getcwd()
		for each_file in os.listdir('.'):
			if each_file[-7] == '.':
				each_file_newname = each_file[:12]+'0'+each_file[12:]
				os.rename(each_file, each_file_newname)
		for each_file in os.listdir('.'):
			if each_file.startswith(query_serial_5digit):
				print each_file
				tracks_count += 1
				query_matches.append(each_file)
				audio = FLAC(each_file)
				audio['tracknumber'] = str(tracks_count)
				audio['artist'] = artist
				audio['album'] = album
				audio.save()
		if tracks_count == 0:
			print 'No spreadsheet matches! Dork.'
		print 'Tracks in #'+query_serial_5digit+':', tracks_count
		print 'Matches:'
		print query_matches

		# Search Discogs for given query
		output = discogs.Search(query).results()
		print 'Results for "'+query+'":', output

		# Print track listing, tag FLAC files with titles
		for result in output:
			if hasattr(result,'tracklist'):
				if len(result.tracklist) == tracks_count:
					print result.artists, result.title
					for track, match in zip(result.tracklist, query_matches):
						print track['title'], track['duration'], match
						audio = FLAC(match)
						audio['title'] = track['title']
						audio.save()
					return
				else:
					print 'Nope!'
		print 'No Discogs matches! Dork.'

add_serial_metadata(input_serial)