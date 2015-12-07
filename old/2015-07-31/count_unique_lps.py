import os
s = set()

for img in os.listdir('c:/temp/'):
	if img.lower().endswith('.jpg'):
		img = img.split('-')[0]
		s.add(img)

print s
print 'Count:', len(s)