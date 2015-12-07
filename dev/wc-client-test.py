from WooCommerceClient import WooCommerceClient
import pprint
import sys
import dropbox

ck = 'ck_bc1ac58b5dc9099c8df1789f811afa2d'
cs = 'cs_7199c23290742677aed84294861ed73b'
base_url = 'https://www.ameryn.com/'
wc_client = WooCommerceClient(ck, cs, base_url)
requested_order_id = 2579
dbox_token = 'asEt1sv4B_0AAAAAAAAFC7AWI6KFNqvxFx2o73NUOLERBg8VxVfsRGSHzqfOqCtL'

#pprint.pprint(wc_client.get_order(requested_order_id))
order = wc_client.get_order(requested_order_id)['order']

# Get variables
cust_email = order['customer']['billing_address']['email']
first_name = order['billing_address']['first_name']
items_text = ''
digital_format = ''
for item in order['line_items']:
    if 'lp' in item['name'].lower() or '45' in item['name'].lower():
        items_text = 'record' if item['quantity'] == 1 else 'records'
    elif 'cassette' in item['name']:
        if items_text:
            items_text += ' and '
        items_text += 'cassette' if item['quantity'] == 1 else 'cassettes'
    for meta in item['meta']:
        if meta['key'] == 'format':
            digital_format = meta['value']
total_items = sum([item['quantity'] for item in order['line_items'] if 'cassette' in item['name'] or 'lp' in item['name'].lower() or '45' in item['name']])
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

# Dropbox
dbox_client = dropbox.client.DropboxClient(dbox_token)
dbox_order_path = str(requested_order_id) # build path here
dbox_link = dbox_client.share(dbox_order_path, short_url=True)['url']

# Printy stuff
print 'Order #{0}'.format(order['id'])
print 'Name: {0} {1}'.format(order['billing_address']['first_name'], order['billing_address']['last_name'])
if order['customer']['billing_address']['email']:
    print 'Email: {0}'.format(cust_email)
else:
    print '--> Error! No email found for {0} {1}.'.format(first_name, order['billing_address']['last_name'])
print 'Items:'
for item in order['line_items']:
    print ' - {0} {1}'.format(item['quantity'], item['name'])
print 'Shipping:', order['shipping_methods']
print ' - - - - - - - - - - - -'

if not digital_format:
    print 'No digital items found for order #{0}.'.format(requested_order_id)
    sys.exit()

# Build email text
emailtext = 'To: {0}'.format(cust_email)
emailtext += '\nHi {0},'.format(first_name)
emailtext += '\nYour {0} order is complete and ready for download with the following link.'.format(digital_format)
if local_pu:
    emailtext += ' Your {0} {1} ready for pickup from our 1702 Latona St office anytime Mon-Fri, 9am - 5pm.'.format(items_text, plural)
elif no_return:
    emailtext += ' We\'ll safely dispose of your {0} after 30 days, or after you\'re satisfied with your order.'.format(items_text)
else:
    emailtext += ' We\'ll return your {0} via USPS {1} Mail tomorrow, and email you a USPS Tracking number.'.format(items_text, shipping_option)
emailtext += ' Thanks for choosing Ameryn Media, and have a great day!'
emailtext += '\nDropbox link: {0}'.format(dbox_link)

print emailtext

# (Finally, set status of WC orders as Ready to Ship)