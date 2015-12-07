def answer(n):
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
    
    for i in range(2, 40):
        if str(convert_base(n, i)) == str(convert_base(n, i))[::-1]:
            return i


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
n = 111
print answer(n)
print '{0} is {1} in base {2}.'.format(n, convert_base(n, answer(n)), answer(n))