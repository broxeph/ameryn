"""
Send Dropbox links to customers.
(c) Ameryn Media LLC, 2015. All rights reserved.
"""

import pprint
from ConfigParser import ConfigParser
from os import path
import smtplib

import dropbox
from WooCommerceClient import WooCommerceClient

import config


def send_dbox_email(order_id, wc_client=None, dbox_client=None, smtp_server=None):
    # Check if Dropbox folder exists
    dbox_order_path = path.join(config.dropbox_folder, order_id)
    if not path.isdir(dbox_order_path):
        print 'No Dropbox folder found for order #{0} at {1}.'.format(order_id, dbox_order_path)
        return

    if not wc_client: wc_client = WooCommerceClient(wc_ck, wc_cs, base_url, oauth_enabled=False)
    order = wc_client.get_order(order_id)['order']

    # Get variables
    cust_email = order['customer']['billing_address']['email']
    first_name = order['billing_address']['first_name'].capitalize()
    last_name = order['billing_address']['last_name'].capitalize()
    cust_name = first_name + ' ' + last_name
    items_text = ''
    digital_format = 'mp3'
    cds = 0
    for item in order['line_items']:
        if 'lp' in item['name'].lower() or '45' in item['name'].lower() and 'lp' not in items_text and '45' not in items_text:
            items_text = 'record' if item['quantity'] == 1 else 'records'
        elif 'cassette' in item['name'] and 'cassette' not in items_text:
            if items_text:
                items_text += ' and '
            items_text += 'cassette' if item['quantity'] == 1 else 'cassettes'
        for meta in item['meta']:
            if meta['key'] == 'mp3-download':
                digital_format = meta['value']
        if 'cd' in item['name'].lower():
            cds += item['quantity']
    total_items = sum([item['quantity'] for item in order['line_items'] if 'cassette' in item['name'] or 'lp' in item['name'].lower() or \
        '45' in item['name']])
    plural = 'is' if total_items == 1 else 'are'
    no_return = True if 'no return' in order['shipping_methods'].lower() else False
    local_pu = True if 'local' in order['shipping_methods'].lower() else False
    if not no_return and not local_pu:
        total_cassettes = sum([item['quantity'] for item in order['line_items'] if 'cassette' in item['name']])
        total_lps = sum([item['quantity'] for item in order['line_items'] if 'lp' in item['name'].lower()])
        total_cd_copies = sum([item['quantity'] for item in order['line_items'] if 'copy' in item['name'].lower()])
        if 'priority' in order['shipping_methods'].lower():
            shipping_option = 'Priority'
        elif total_cassettes + total_cd_copies <= 4 and not total_lps:
            shipping_option = 'First Class'
        else:
            shipping_option = 'Media'
    if cds:
        cds_text = ' and CD'
        if cds > 1:
            cds_text += 's'
    else:
        cds_text = ''

    # Dropbox link
    if not dbox_client: dbox_client = dropbox.client.DropboxClient(config.dbox_token)
    dbox_order_path = order_id
    dbox_link = dbox_client.share(dbox_order_path, short_url=True)['url']

    # Printy stuff
    print ' - - - - - - - - - - - -'
    print 'Order #{0}'.format(order['id'])
    print 'Name: {0}'.format(cust_name)
    if order['customer']['billing_address']['email']:
        print 'Email: {0}'.format(cust_email)
    else:
        print '--> Error! No email found for {0}.'.format(cust_name)
    print 'Items:'
    for item in order['line_items']:
        print ' - {0} {1}'.format(item['quantity'], item['name'])
    print 'Shipping:', order['shipping_methods']

    if not digital_format:
        print 'No digital items found for order #{0}.'.format(order_id)
        return

    # Build email text
    emailtext = 'Hi {0},\n\n'.format(first_name)
    emailtext += 'Your {0} order #{1} is complete and ready for download with the following link.'.format(digital_format, order_id)
    if local_pu:
        emailtext += ' Your {0} {1} ready for pickup from our 1702 Latona St office anytime Mon-Fri, 9am - 5pm.\n\n'.format(items_text, plural)
    elif no_return:
        emailtext += ' We\'ll safely dispose of your {0} after 30 days, or after you\'re satisfied with your order.\n\n'.format(items_text)
    else:
        emailtext += ' We\'ll return your {0}{1} via USPS {2} Mail, and email you a USPS Tracking number.\n\n'.format(items_text,
            cds_text, shipping_option)
    emailtext += 'Download link: {0}\n\n'.format(dbox_link)
    emailtext += 'If you have any questions, feel free to reply to this email or call us at (844) AMERYN-1.'
    emailtext += ' Thanks for choosing Ameryn Media, and have a great day!\n\n'

    # Prepare actual message
    message = 'From: Ameryn Media <orders@ameryn.com>\n'
    message += 'To: {0} <{1}>\n'.format(cust_name, cust_email)
    message += 'Subject: Ameryn Media - Your {0} download is ready!\n\n'.format(digital_format)
    message += emailtext

    #print ' - - - - - - - - - - - -'
    #print message
    #print ' - - - - - - - - - - - -'

    # Send the mail
    if smtp_server:
        smtp_server.sendmail('orders@ameryn.com', [cust_email, 'test@ameryn.com'], message)
    else:
        smtp_server = smtplib.SMTP('smtp-relay.gmail.com', 587)
        smtp_server.starttls()
        smtp_server.login('alex@ameryn.com', 'calselptbnympllf')
        smtp_server.sendmail('orders@ameryn.com', [cust_email, 'test@ameryn.com'], message)

    # Mark no-return, local orders as Complete/Ready in WC
    if no_return:
        wc_client.update_order(order_id, '{"order": {"status": "completed"}}')
        return order_id
    elif local_pu:        
        wc_client.update_order(order_id, '{"order": {"status": "pending-pickup"}}')
    return None

def send_all(order_ids):    
    wc_client = WooCommerceClient(config.wc_ck, config.wc_cs, config.base_url, oauth_enabled=False)
    dbox_client = dropbox.client.DropboxClient(config.dbox_token)    
    smtp_server = smtplib.SMTP('smtp-relay.gmail.com', 587)
    smtp_server.starttls()
    smtp_server.login('alex@ameryn.com', 'calselptbnympllf')
    discard_list = []
    for each_order in order_ids:
        if send_dbox_email(each_order, wc_client, dbox_client, smtp_server):
            discard_list.append(each_order)
    smtp_server.quit()
    if discard_list:
        print ' - - - - - - - - - - -'
        print 'Discard list:'
        for each_order in discard_list:
            print ' -', each_order

if __name__ == '__main__':
    send_all(['2979', '2962', '2948', '2992', '2994', '2995', '2996', '2998', '3086'])