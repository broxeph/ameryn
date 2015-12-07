import re
import sys

with open('time.txt') as f:
	lines = f.readlines()

'''
done = False
for i in range(10,0,-1):
	pattern = '[aeiouy]' * i
	print pattern
	for n, line in enumerate(lines):
		match = re.search(pattern, line)
		if match:
			print n, line
			done = True
	if done == True:
		break
'''


#lines = ['aoeuaoeu1223-23-12aoeu']
pattern = '[aeiou]'
for n, line in enumerate(lines):
	match = re.search(pattern, line)
	if match:
		#print n, match.group(), line
		print n, line