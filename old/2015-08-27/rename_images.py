"""
Batch-rename image folder with item titles
"""

import os
import csv
import string

import config

IMAGES_FOLDER = 'F:/Dropbox/3032/Images'
images = [image for image in os.listdir(IMAGES_FOLDER) if image.startswith('03') and os.path.splitext(image)[-1] == '.jpg']
print images

with open(config.db_path, 'r') as items:
    rows = csv.reader(items)
    for image in images:
        for row in rows:
            if row[0] == os.path.splitext(image)[0]:
                if row[1] and row[2]:
                    name = row[1] + ' - ' + row[2]
                elif row[1] or row[2]:
                    name = (row[1] or row[2])
                else:
                    name = 'Untitled - ' + row[0]                
                name = name.replace(':', ' -')
                name = name.translate(None, '<>:|?*') # Windows allowed filename chars
                name = name.translate(string.maketrans('"/\\', '\'--'))
                name += os.path.splitext(image)[-1]
                print row[0], name
                os.rename(os.path.join(IMAGES_FOLDER, image), os.path.join(IMAGES_FOLDER, name))
                break