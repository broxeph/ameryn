'''
Various utilities for metadata processing
(C) 2015 Ameryn Media, LLC
'''

import os
import HTMLParser
from item import Item

from WooCommerceClient import WooCommerceClient

import config
import utils

def print_order_notes(item_list=None, refresh_csv=True):
    if not item_list:
        # Input whole Tracked folder
        print "Item-izing tracked folder...",
        item_list = [Item(each_file) for each_file in os.listdir(config.tracked_folder) if os.path.splitext(each_file)[-1] == '.wav']
        print "Done."

    if refresh_csv:
        utils.export_csv('Items') # Grab spreadsheet from Google Drive

    # items.csv item notes
    notes_lines = [' - items.csv -']
    for item in [item for item in item_list if not item.copy_counter and not item.side]:
        if item.customer_notes:
            notes_lines.append('{0} - Customer notes: {1}'.format(item.name, item.customer_notes))
        if item.private_notes and len(item.private_notes) > 3:
            notes_lines.append('{0} - Private notes: {1}'.format(item.name, item.private_notes))

    # WooCommerce order notes
    notes_lines.append(' - WC notes -')
    wc_client = WooCommerceClient(config.wc_ck, config.wc_cs, config.base_url, oauth_enabled=False)
    for order_id in sorted(set([item.order.lstrip('0') for item in item_list])):
        order = wc_client.get_order(order_id)['order']
        html_parser = HTMLParser.HTMLParser()
        notes_lines.append('{0} - {1}'.format(order_id, html_parser.unescape(order['note'])))
        if not order['payment_details']['paid']:
            notes_lines.append('{0} - UNPAID'.format(order_id))

    # Print notes; write to text file
    for notes_line in notes_lines:
        print notes_line
    order_notes_file = os.path.join(config.order_notes_folder, 'order_notes.txt')
    with open(order_notes_file, 'w') as notes:
        for notes_line in notes_lines:
            notes.write(notes_line + '\n')

    # Open notes in default text editor
    os.startfile(order_notes_file)

if __name__ == '__main__':
    print_order_notes(refresh_csv=False)