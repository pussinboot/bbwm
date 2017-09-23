from collections import namedtuple


class Dims(namedtuple('Dims', ['x', 'y', 'w', 'h'])):
    __slots__ = ()

    def __str__(self):
        return '@ ({:4d},{:4d}) | w: {:4d} h: {:4d}'.format(self.x, self.y, self.w, self.h)

    def split_h(self, r=0.5):
        new_w = int(self.w * r)
        d1 = Dims(self.x, self.y, new_w, self.h)
        d2 = Dims(self.x + new_w, self.y, self.w - new_w, self.h)
        return d1, d2

    def split_h_n(self, n):
        if n <= 2:
            return self.split_h()
        new_w = self.w // n
        tor = []
        for i in range(n - 1):
            tor.append(Dims(self.x + i * new_w, self.y, new_w, self.h))
        final_w = self.w - (n - 1) * new_w  # for rounding errors
        tor.append(Dims(self.x + self.w - final_w, self.y, final_w, self.h))
        return tor

    def split_v(self, r=0.5):
        new_h = int(self.h * r)
        d1 = Dims(self.x, self.y, self.w, new_h)
        d2 = Dims(self.x, self.y + new_h, self.w, self.h - new_h)
        return d1, d2

    def split_v_n(self, n):
        if n <= 2:
            return self.split_v()
        new_h = self.h // n
        tor = []
        for i in range(n - 1):
            tor.append(Dims(self.x, self.y + i * new_h, self.w, new_h))
        final_h = self.h - (n - 1) * new_h  # for rounding errors
        tor.append(Dims(self.x, self.y + self.h - final_h, self.w, final_h))
        return tor

    def resize(self, d, r, i):
        if d == 'v':
            return self.split_v(r)[i]
        else:
            return self.split_h(r)[i]

    def resize_n(self, d, n, i):
        if d == 'v':
            return self.split_v_n(n)[i]
        else:
            return self.split_h_n(n)[i]

    def midpoint(self):
        return self.x + (self.w // 2), self.y + (self.h // 2)

    def distance_to(self, x2, y2):
        # manhattan dist
        x1, y1 = self.midpoint()
        return abs(x1 - x2) + abs(y1 - y2)

    def adjacency_check(self, o, i):
        # among our dimension make sure touching
        return (self[i] == o[i] + o[i + 2] or o[i] == self[i] + self[i + 2]) and \
               ((o[1 - i] <= self[1 - i] and (o[1 - i] + o[3 - i]) > self[1 - i]) or
               (o[1 - i] > self[1 - i] and o[1 - i] < (self[1 - i] + self[3 - i])))

    def _get_offset_dims(self, lo, to, ro, bo):
        x, w = self.x + lo, self.w - lo - ro
        y, h = self.y + to, self.h - to - bo
        return Dims(x, y, w, h)

    def get_win_dims(self, c):
        xo, yo = c.INNER_SPACING_X, c.INNER_SPACING_Y
        return self._get_offset_dims(xo, yo, xo, yo)

    def get_ws_dims(self, c):
        return self._get_offset_dims(*c.BORDER_OFFSETS)


class Split(namedtuple('Split', ['d', 'r', 't'])):
    # direction, ratio and index
    # direction can be either
    # h - horizontal
    # v - vertical
    # n - neither
    # ratio is a float between 0 and 1
    # t = type
    __slots__ = ()

    def __str__(self):
        return 'split : (d: {}, r: {:01.3f})'.format(self.d, self.r)

    def __new__(cls, d, r, t=None):
        return super(Split, cls).__new__(cls, d, r, t)

