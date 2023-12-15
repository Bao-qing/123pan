import time
import random
from datetime import datetime


def getSign(e):
    def unsigned_right_shift(n, shift):
        return (n % 0x100000000) >> shift

    def simulate_js_overflow(js_int, n):
        # 转二进制
        if js_int < 0:
            js_int = -js_int
            js_int = str(bin(js_int))[2:]
            js_int = js_int.zfill(32)
            js_int = js_int.replace("0", "2")
            js_int = js_int.replace("1", "0")
            js_int = js_int.replace("2", "1")
            js_int = int(js_int, 2) + 1
        bin_int = str(bin(js_int))[2:].zfill(32)
        if n < 0:
            # 转补码
            n = -n
            n = str(bin(n))[2:]
            n = n.zfill(32)
            n = n.replace("0", "2")
            n = n.replace("1", "0")
            n = n.replace("2", "1")
            n = int(n, 2) + 1
        bin_n = str(bin(n))[2:].zfill(32)
        result = ""
        for i in range(0, len(bin_int)):
            temp = int(bin_n[i]) ^ int(bin_int[i])
            result = result + str(temp)
        if result[0] == "1":
            # 取补码
            result = result.replace("0", "2")
            result = result.replace("1", "0")
            result = result.replace("2", "1")
            result = int(result, 2) + 1
            result = -result
        else:
            result = int(result, 2)
        return result

    def A(t):
        r = t.replace('\r\n', '\n')
        a = -1

        def generate_array():
            t = []
            for e in range(256):
                n = e
                for _ in range(8):
                    if n & 1:  # 如果 n 的最低位是 1
                        # print("入口：n：", n)
                        n = simulate_js_overflow(3988292384, unsigned_right_shift(n, 1))
                    else:
                        n = unsigned_right_shift(n, 1)
                t.append(n)
            return t

        n = generate_array()
        # print(n)
        for i in range(len(r)):
            # print("a:", unsigned_right_shift(a, 8))
            a = unsigned_right_shift(a, 8) ^ n[255 & (a ^ ord(r[i]))]
        # print("zz", a)
        return str((simulate_js_overflow(-1, a)) & 0xFFFFFFFF)

    def generate_timestamp():
        return round((time.time() + datetime.now().astimezone().utcoffset().total_seconds() + 28800) / 1)

    def adjust_timestamp(o, timestamp):
        if timestamp:
            i = timestamp
            m = i
            if 20 <= abs(1000 * o - 1000 * int(m)) / 1000 / 60:
                return i
        return o

    def formatDate(t, e=None, n=8):
        t = int(t)  # Use the original timestamp
        t = t - 480 * 60
        r = datetime.fromtimestamp(t + 3600 * n)  # Convert to seconds and add 'n' hours
        data = {
            'y': str(r.year),
            'm': f"0{r.month}" if r.month < 10 else str(r.month),
            'd': f"0{r.day}" if r.day < 10 else str(r.day),
            'h': f"0{r.hour}" if r.hour < 10 else str(r.hour),
            'f': f"0{r.minute}" if r.minute < 10 else str(r.minute)
        }
        return data

    def generate_signature(a, o, e, n, r):
        s = ["a", "d", "e", "f", "g", "h", "l", "m", "y", "i", "j", "n", "o", "p", "k", "q", "r", "s", "t", "u", "b",
             "c", "v", "w", "s", "z"]
        u = formatDate(o)
        h = u['y']
        g = u['m']
        l = u['d']
        c = u['h']
        u = u['f']
        d = ''.join([h, g, l, c, u])
        f = [s[int(p)] for p in d]
        h = A(''.join(f))
        g = A(f"{o}|{a}|{e}|{n}|{r}|{h}")
        return [h, f"{o}-{a}-{g}"]

    a = str(random.randint(0, 9999999))
    o = generate_timestamp()
    o = adjust_timestamp(o, timestamp=round(time.time()))

    n = "web"
    r = '3'
    return generate_signature(a, o, e, n, r)


if __name__ == '__main__':
    e = '/b/api/file/list/new'
    print(getSign(e))
