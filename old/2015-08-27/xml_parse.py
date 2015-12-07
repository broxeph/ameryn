'''
import xml.etree.cElementTree as etree
infile = open('c:/users/alex/downloads/discogs_20140601_artists.xml', 'r')
context = etree.iterparse(infile)

for event, element in context:
	if element.tag == 'name':
		print element.text
	elif element.tag in ['namevariations']:
		print '---', element.text.encode('utf-8')
'''

import mmap
import xml.etree.cElementTree as etree

with open('c:/users/alex/downloads/discogs_20140601_artists.xml', 'rb') as f:
	# Size 0 will read the ENTIRE file into memory!
	m = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) #File is open read-only
	try:
		context = etree.parse(m)
	except:
		pass

	'''
	for event, element in context:
		if element.tag == 'name':
			print element.text
		elif element.tag in ['namevariations']:
			print '---', element.text.encode('utf-8')
	'''