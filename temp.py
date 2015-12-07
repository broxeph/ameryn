"""
Batch-rename image folder with item titles
"""

import os
import csv

import config


images = os.listdir('F:/Dropbox/3032/Images')
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
                print row[0], name
                break