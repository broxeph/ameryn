n = 20

def convert_base(in_num, out_base):
	output = []
	for i in range(40):
		if out_base**(i + 1) > in_num:
			output.append(str(in_num / out_base**i))
			in_num = in_num % out_base**i
			for j in range(i - 1, -1, -1):
				if out_base**j <= in_num:
					output.append(str(in_num / out_base**j))
				else:
					output.append('0')
				in_num = in_num % out_base**j
			return ''.join(output)

def check_palindrome(in_num):
	return str(in_num) == str(in_num)[::-1]

def answer(n):
	for i in range(2, 40):
		if check_palindrome(convert_base(n, i)):
			return i

if __name__ == '__main__':
	print '{0} is {1} in base {2}.'.format(n, convert_base(n, answer(n)), answer(n))