'''
Various utilities for metadata processing
(C) 2015 Ameryn Media, LLC
'''

import csv
import os

from oauth2client.client import SignedJwtAssertionCredentials
import gspread

import config

def export_csv(input_sheets):
    credentials = SignedJwtAssertionCredentials(config.drive_client_email, config.drive_private_key, ['https://spreadsheets.google.com/feeds'])
    gc = gspread.authorize(credentials)

    if not isinstance(input_sheets, list): input_sheets = [input_sheets]        
    for each_sheet in input_sheets:
        sheet = gc.open(each_sheet).sheet1
        output_fname = os.path.join(config.csv_folder, each_sheet.lower()).translate(None, '!') + '.csv'
        everything = [[col.encode('utf-8') for col in row] for row in sheet.get_all_values()]

        with open(output_fname, 'wb') as f:
            writer = csv.writer(f)
            writer.writerows(everything)