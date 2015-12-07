import os
from PIL import Image, ImageOps

#input_name = 'test_pic.jpg'
input_folder = 'C:\Users\Alex\Google Drive\Crystal\WTUL\Scripts\imgy temp'
record_type = 'lp'
crop_size = {
	'lp_tall': (0, 832, 3264, 4096),
	'lp_wide': (832, 0, 4096, 3264),
	'7_tall': (0, 832, 1900, 2732),
	'7_wide': (832, 1364, 2732, 3264),
	}

for each_file in os.listdir(input_folder):
	print each_file
	if each_file.lower().endswith('.jpg'):
		im = Image.open(os.path.join(input_folder, each_file))
		if record_type == 'lp' and im.size == (3264, 4928):
			box = crop_size['lp_tall']
		elif record_type == 'lp' and im.size == (4928, 3264):
			box = crop_size['lp_wide']
		elif record_type == '7' and im.size == (3264, 4928):
			box = crop_size['7_tall']
		elif record_type == '7' and im.size == (4928, 3264):
			box = crop_size['7_wide']
		region = im.crop(box)
		region = ImageOps.autocontrast(region, 1)
		region = region.rotate(270)
		region.save(os.path.join(input_folder, each_file))