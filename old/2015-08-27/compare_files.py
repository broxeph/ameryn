import os, logging
logging.basicConfig(filename='different_files.log', format='%(message)s', level=logging.INFO)
d = 'Q:/WTUL-1/02 cut'
e = 'Q:/WTUL-1/03 clean'

for f in sorted(os.listdir(d)):
	if f.endswith('.wav'):
		if int(f[:5]) < 6600:
			if not os.path.isfile(e + '/' + f[:-4] + '_clean' + f[-4:]):
				print 'Not found:', f
				logging.info('%s', f)
			else:
				print f