import math

import numpy

COLUMNS = 10

with open('order_totals.txt', 'r') as txt:
	totals = [float(each.rstrip('\n')) for each in txt.readlines()]

print 'totals:', totals
print 'median:', numpy.median(totals)
print 'mean:', round(numpy.mean(totals), 2)
print 'totals max:', max(totals)
totals_log = int(math.log10(max(totals)))+1
print 'totals_log:', totals_log
chart_max = int(round(max(totals) * 1.1, -(totals_log-2)))
#cols = [chart_max * each / COLUMNS for each in range(0,COLUMNS + 1)]
cols = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 2000]
print 'columns:', cols

for i in range(len(cols) - 1):
	print '{0}-{1}: {2}'.format(cols[i], cols[i + 1], sum([each for each in totals if cols[i] < each < cols[i + 1]]))