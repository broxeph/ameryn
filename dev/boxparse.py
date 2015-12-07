#hey imma parse ur boxes ok

import csv
from mutagen.flac import FLAC

#discogs.user_agent = 'CrystalDiscogsBot/0.1 +http://www.crystal-lp.com'

with open('boxes.csv', 'r') as boxes:
	spamreader = csv.reader(boxes)
	print 'Hello, world!'
	rowdata = []
	for row in spamreader:
		rowdata.append(row)
	rowInput = 14
	for row in rowdata:
		if row[0] == str(rowInput):
			print 'Match!'
			print 'RealRow:',row
			audio = FLAC('fong1.flac')
			audio['title'] = row[0]
			audio['artist'] = row[1]
			audio['album'] = row[2]
			audio.pprint()
			audio.save()
			break
	else:
		print 'No match found.'
	print