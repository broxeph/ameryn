from woocommerce import API
import pprint
import json

wcapi = API(
    url="https://www.ameryn.com/",
    consumer_key="ck_bc1ac58b5dc9099c8df1789f811afa2d",
    consumer_secret="cs_7199c23290742677aed84294861ed73b",
    version='v2',
    verify_ssl=True
)

print wcapi
#order = wcapi.get('recording_orders/3050').json()
recording_orders = wcapi.get('orders?status=recording&filter[limit]=100').json()['orders']
#print json.dumps(order, indent=4)
for each_order in recording_orders:
    print each_order['id'], '-', each_order['status'], '-', each_order['billing_address']['email'], '-', '$' + each_order['total']
print '{0} recording_orders, ${1}'.format(str(len(recording_orders)), sum([float(each_order['total']) for each_order in recording_orders]))
#print [order['id'] for order in wcapi.get('recording_orders?status=recording&fields=id&filter[limit]=100').json()['recording_orders']]

all_orders = wcapi.get('orders?filter[limit]=2000').json()['orders']
all_order_totals = [float(each_order['total']) for each_order in all_orders]

print all_order_totals
print '{0} orders, ${1}'.format(str(len(all_orders)), sum(all_order_totals))

print 'Creating new text file'
with open('order_totals.txt', 'w') as txt:
	txt.writelines([str(each) for each in all_order_totals])