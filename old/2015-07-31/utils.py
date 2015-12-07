'''
Various utilities for metadata processing
(C) 2015 Ameryn Media, LLC
'''

import csv
import os
import HTMLParser

from oauth2client.client import SignedJwtAssertionCredentials
import gspread
from WooCommerceClient import WooCommerceClient

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

def print_order_notes(item_list):
    # items.csv item notes
    notes_lines = [' - items.csv -']
    for item in [item for item in item_list if not item.copy_counter and not item.side]:
        if item.customer_notes:
            notes_lines.append('{0} - Customer notes: {1}'.format(item.name, item.customer_notes))

    # WooCommerce order notes
    notes_lines.append(' - WC notes -')
    wc_client = WooCommerceClient(config.wc_ck, config.wc_cs, config.base_url, oauth_enabled=False)
    for order_id in set([item.order.lstrip('0') for item in item_list]):
        order = wc_client.get_order(order_id)['order']
        html_parser = HTMLParser.HTMLParser()
        notes_lines.append('{0} - {1}'.format(order_id, html_parser.unescape(order['note'])))

    # Print notes; write to text file
    for notes_line in notes_lines:
        print notes_line
    order_notes_file = os.path.join(config.order_notes_folder, 'order_notes.txt')
    with open(order_notes_file, 'w') as notes:
        for notes_line in notes_lines:
            notes.write(notes_line + '\n')

    # Open notes in default text editor
    os.startfile(order_notes_file)