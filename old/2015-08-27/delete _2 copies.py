import os

input_folder = 'Q:/WTUL-1/07 images'
dupes = 0

for each_file in os.listdir(input_folder):
	each_file = os.path.join(input_folder, each_file)
	#print each_file
	possible_dupe = os.path.join(input_folder, os.path.splitext(each_file)[0]+'_1.jpg')
	if os.path.isfile(possible_dupe):
		if os.path.getsize(each_file) == os.path.getsize(possible_dupe):
			print 'Duplicate:', possible_dupe
			dupes += 1
			os.remove(possible_dupe)

print 'Done! Dupes found:', dupes
