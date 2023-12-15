function v(t) {
    return (v = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function (t) {
                return typeof t
            }
            : function (t) {
                return t && "function" == typeof Symbol && t.constructor === Symbol && t !== Symbol.prototype ? "symbol" : typeof t
            }
    )(t)
}

function A(t, e) {
    e = 1 < arguments.length && void 0 !== e ? e : 10;
    for (var n = function () {
        for (var t = [], e = 0; e < 256; e++) {
            for (var n = e, r = 0; r < 8; r++)
                n = 1 & n ? 3988292384 ^ n >>> 1 : n >>> 1;
            t[e] = n
        }
        return t
    }(), r = function (t) {
        t = t.replace(/\\r\\n/g, "\\n");
        for (var e = "", n = 0; n < t.length; n++) {
            var r = t.charCodeAt(n);
            r < 128 ? e += String.fromCharCode(r) : e = 127 < r && r < 2048 ? (e += String.fromCharCode(r >> 6 | 192)) + String.fromCharCode(63 & r | 128) : (e = (e += String.fromCharCode(r >> 12 | 224)) + String.fromCharCode(r >> 6 & 63 | 128)) + String.fromCharCode(63 & r | 128)
        }
        return e
    }(t), a = -1, i = 0; i < r.length; i++)
        a = a >>> 8 ^ n[255 & (a ^ r.charCodeAt(i))];
    return (a = (-1 ^ a) >>> 0).toString(e)
}


global.e = '/b/api/file/list/new'
global.n = "web"
global.r = 3
global.timestamp = 1702555131
for (p in a = Math.round(1e7 * Math.random()),
    o = Math.round(((new Date).getTime() + 60 * (new Date).getTimezoneOffset() * 1e3 + 288e5) / 1e3).toString(),
timestamp && (i = timestamp),
    o = i && (m = i,
    20 <= Math.abs(1e3 * o - 1e3 * m) / 1e3 / 60) ? i : o,
    s = atob((m = void 0,
        m = ["a", "d", "e", "f", "g", "h", "l", "m", "y", "i", "j", "n", "o", "p", "k", "q", "r", "s", "t", "u", "b", "c", "v", "w", "s", "z"].join(","),
        btoa(m))).split(","),
    u = function (t, e, n) {
        var r;
        n = 2 < arguments.length && void 0 !== n ? n : 8;
        return 0 === arguments.length ? null : (r = "object" === v(t) ? t : (10 === "".concat(t).length && (t = 1e3 * Number.parseInt(t)),
            new Date(t)),
            t += 6e4 * new Date(t).getTimezoneOffset(),
            {
                y: (r = new Date(t + 36e5 * n)).getFullYear(),
                m: r.getMonth() + 1 < 10 ? "0".concat(r.getMonth() + 1) : r.getMonth() + 1,
                d: r.getDate() < 10 ? "0".concat(r.getDate()) : r.getDate(),
                h: r.getHours() < 10 ? "0".concat(r.getHours()) : r.getHours(),
                f: r.getMinutes() < 10 ? "0".concat(r.getMinutes()) : r.getMinutes()
            })
    }(o),
    h = u.y,
    g = u.m,
    l = u.d,
    c = u.h,
    u = u.f,
    d = [h, g, l, c, u].join(""),
    f = [],
    d)
    f.push(s[Number(d[p])]);
h = A(f.join(""));
g = A("".concat(o, "|").concat(a, "|").concat(e, "|").concat(n, "|").concat(r, "|").concat(h));
console.log([h, "".concat(o, "-").concat(a, "-").concat(g)]);