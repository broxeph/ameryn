import multiprocessing

def f(x):
	return x/13.99848645*2343.5484*3.23413

#'''
if __name__ == '__main__':
	pool = multiprocessing.Pool(multiprocessing.cpu_count() - 1)
	#result = pool.apply_async(f, [10])
	#print result.get(timeout=1)
	pool.map(f, range(100000000))
#'''

#print map(f, range(10000))