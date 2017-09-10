from collections import namedtuple
import abc


# geometry
class Dims(namedtuple('Dims', ['x', 'y', 'w', 'h'])):
    __slots__ = ()

    def __str__(self):
        return '@ ({:4d},{:4d}) | w: {:4d} h: {:4d}'.format(self.x, self.y, self.w, self.h)

    def split_h(self, r=0.5):
        new_w = int(self.w * r)
        d1 = Dims(self.x, self.y, new_w, self.h)
        d2 = Dims(self.x + new_w, self.y, self.w - new_w, self.h)
        return d1, d2

    def split_v(self, r=0.5):
        new_h = int(self.h * r)
        d1 = Dims(self.x, self.y, self.w, new_h)
        d2 = Dims(self.x, self.y + new_h, self.w, self.h - new_h)
        return d1, d2

    def resize(self, d, r, i):
        if d == 'v':
            return self.split_v(r)[i]
        else:
            return self.split_h(r)[i]

    def midpoint(self):
        return self.x + (self.w // 2), self.y + (self.h // 2)

    def distance_to(self, x2, y2):
        # manhattan dist
        x1, y1 = self.midpoint()
        return abs(x1 - x2) + abs(y1 - y2)

    def adjacency_check(self, o, i):
        # among our dimension make sure touching
        return (self[i] == o[i] + o[i + 2] or o[i] == self[i] + self[i + 2]) and \
               ((o[1 - i] <= self[1 - i] and (o[1 - i] + o[3 - i]) > self[1 - i]) or \
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


class Split(namedtuple('Split', ['d', 'r'])):
    # direction, ratio and index
    # direction can be either
    # h - horizontal
    # v - vertical
    # n - neither
    # ratio is a float between 0 and 1
    __slots__ = ()

    def __str__(self):
        return 'split : (d: {}, r: {:01.3f})'.format(self.d, self.r)


# boxing
class Workspace:
    # a workspace is like a super-partition
    def __init__(self, base_dims, tile_scheme=None, first_child=None):
        self.base_dims = base_dims

        if tile_scheme is None:
            tile_scheme = DefaultTilingScheme()
        self.tile_scheme = tile_scheme

        if first_child is None:
            first_child = Partition(None, self.base_dims)
        else:
            first_child.parent = self
            first_child.dims = self.base_dims

        self.children = [first_child]
        self.cur_part = first_child

        # for pseudo-partitions
        self.parent = None
        self.split = None

        # moving around
        self.go_left = lambda: self._move('h', -1)
        self.go_right = lambda: self._move('h', 1)
        self.go_up = lambda: self._move('v', -1)
        self.go_down = lambda: self._move('v', 1)

    def _str_help(self, part, prefix=""):
        tor = ["{}{}".format(prefix, part.__str__())]
        pref = "\t{}".format(prefix)
        for p in part:
            tor.extend(self._str_help(p, pref))
        return tor

    def __str__(self):
        all_str = self._str_help(self.children[0])
        return "\n".join(all_str)

    def __iter__(self):
        for b in self.children:
            yield b

    def _full_traversal(self, part):
        tor = [part]
        for p in part:
            tor.extend(self._full_traversal(p))
        return tor

    def _traverse(self, part=None, filter_fun=None):
        # either do full traversal
        # or only return the nodes that match a filter function
        if part is None:
            part = self.children[0]
        if filter_fun is None:
            return self._full_traversal(part)
        tor = []
        for p in part:
            if filter_fun(p):
                tor.append(p)
            tor.extend(self._traverse(p, filter_fun))
        return tor

    def _bottom_up_traverse(self, part):
        tor = [part]
        # actually nvm the partition isinstance check.. if i want workspaces within
        if part.parent is not None:
            tor.extend(self._bottom_up_traverse(part.parent))
        return tor

    def find_leaf_parts(self, root=None):
        if root is None:
            root = self
        return self._traverse(root, lambda p: p.is_empty)

    def find_neighbors(self, d, root=None):
        if root is None:
            root = self.cur_part
        i = 1 if d == 'v' else 0

        # find all partitions that were split in the direction we're looking for
        # from the bottom up
        cands = self._bottom_up_traverse(root)
        one_dir = [p for p in cands if p.split is not None and p.split.d == d]
        # get all their leaves
        all_p = []
        for c in one_dir:
            all_p.extend(self.find_leaf_parts(c))

        # now only do ones that touch..
        fil_p = [p for p in all_p if p.dims.adjacency_check(root.dims, i)]
        fil_p.append(root)
        fil_p = list(set(fil_p))

        # sort them
        fil_p.sort(key=lambda p: p.dims[i])
        return fil_p

    def find_valid_moves(self, d, n):
        cp = self.cur_part
        n_ps = self.find_neighbors(d)
        i = n_ps.index(cp)
        new_i = i + n
        if new_i < 0 or new_i >= len(n_ps):
            return  # no wraparound..
        # now sort by distance
        next_ps = n_ps[new_i::n]
        return next_ps

    def _move(self, d, n):
        cp = self.cur_part
        axis = 1 if d == 'v' else 0

        n_ps = self.find_neighbors(d)
        i = n_ps.index(cp)
        new_i = i + n
        if new_i < 0 or new_i >= len(n_ps):
            return  # no wraparound..
        # now sort by distance
        next_ps = n_ps[new_i::n]
        # want closest to corner
        x = cp.dims[0]  # + (1 + n) // 2 * cp.dims[2]
        # xor to add height
        y = cp.dims[1] + cp.dims[3] * (bool((1 - n) // 2) != bool(axis))

        next_ps.sort(key=lambda p: p.dims.distance_to(x, y))
        self.cur_part = next_ps[0]

    def split_h(self, r=0.5, new_win=None):
        np = self.cur_part.split_h(r, new_win)
        if np is not None:
            self.cur_part = np

    def split_v(self, r=0.5, new_win=None):
        np = self.cur_part.split_v(r, new_win)
        if np is not None:
            self.cur_part = np

    def tile(self, new_win=None):
        np = self.tile_scheme.tile(self.cur_part, new_win)
        if np is not None:
            self.cur_part = np

    def untile(self, part=None):
        if part is None:
            cp = self.cur_part
        else:
            cp = part
        if cp.parent is None:
            return
        if cp.index >= len(cp.parent.children):
            return

        # get rid of the partition and reassign indices

        del cp.parent.children[cp.index]

        if len(cp.parent.children) == 1:
            cp.parent.become_child()
            next_cur = cp.parent
        else:
            new_i = max(0, cp.index - 1)
            for i, c in enumerate(cp.parent.children):
                c.index = i
            next_cur = cp.parent.children[new_i]

        if part == self.cur_part:
            # if the partition we untiled was current
            # reassign to closest leaf partition
            if next_cur.is_empty:
                self.cur_part = next_cur
            else:
                self.cur_part = self.find_leaf_parts(next_cur)[0]

        # now recompute all dims because this doesnt work...
        # aff_parts = self._traverse(self.cur_part.parent)
        aff_parts = self._traverse()

        for p in aff_parts:
            p.resize_from_parent()

    def resize_from_parent(self):
        pass



class Partition:
    def __init__(self, parent, dims, index=0, win=None):
        self.parent = parent
        self.children = []

        self.dims = dims
        self.index = index
        self.split = None
        self.window = win
        if self.window is not None:
            self.window.part = self

    @property
    def is_empty(self):
        return len(self.children) == 0

    @property
    def siblings(self):
        if self.parent is not None:
            return self.parent.children
        return []

    def __iter__(self):
        for b in self.children:
            yield b

    def __str__(self):
        s = 'part (#{}) {}'.format(self.index, self.dims.__str__())
        if self.split is not None:
            s = '{} | {}'.format(s, self.split.__str__())
        if self.window is not None:
            s = '{} | win : {}'.format(s, self.window.hwnd)
        return s

    def become_child(self, idx=0):
        new_me = self.children[idx]

        self.children = new_me.children
        # aah
        for c in self.children:
            c.parent = self
        self.split = new_me.split
        self.window = new_me.window
        if self.window is not None:
            self.window.part = self

    def resize_from_parent(self):
        if self.parent is None:
            return
        if self.parent.split is None:
            return
        d, r = self.parent.split.d, self.parent.split.r
        self.dims = self.parent.dims.resize(d, r, self.index)

    def _split(self, d, r, new_win):
        if d == 'h':
            sf = self.dims.split_h
        elif d == 'v':
            sf = self.dims.split_v
        else:
            # adding tabs?
            return

        dim1, dim2 = sf(r)
        # move current window into first partition
        p1 = Partition(self, dim1, 0, self.window)
        self.window = None
        # any new window goes into second
        p2 = Partition(self, dim2, 1, new_win)
        # and now we know how we were split
        self.split = Split(d, r)
        self.children.extend([p1, p2])
        if new_win is None:
            return p1
        return p2

    def split_h(self, r=0.5, new_win=None):
        return self._split('h', r, new_win)

    def split_v(self, r=0.5, new_win=None):
        return self._split('v', r, new_win)


# tiling logic
class TileScheme:
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        pass

    @abc.abstractmethod
    def tile(self, part, new_win=None):
        return

    @abc.abstractmethod
    def untile(self, part):
        return


class DefaultTilingScheme(TileScheme):
    def __init__(self):
        super().__init__()
        self.tile_count = 0

    def tile(self, part, new_win=None):
        if new_win is not None:
            if new_win.part is not None:
                # don't retile
                return
            elif part.window is None:
                # first add to current partition if it's empty
                part.window = new_win
                new_win.part = part
                return
        if self.tile_count == 0:
            np = part.split_h(0.67, new_win)
        else:
            np = part.split_v(0.5, new_win)
        if np is not None:
            self.tile_count += 1
            return np

    def untile(self, part, new_win=None):
        self.tile_count = max(0, self.tile_count - 1)


# configuration
class Config:
    def __init__(self):


        # left, top, right, bottom
        self.BORDER_OFFSETS = [25, 30, 25, 20]
        self.OFF_SCREEN = max(self.BORDER_OFFSETS) + 20

        # inner spacing
        self.INNER_SPACING_X = 10
        self.INNER_SPACING_Y = 10

        # sizes
        self.CURSOR_SIZE = 20

        # colors
        self.BORDER_HIGHLIGHT_COLOR = 'gray'
        self.BORDER_COLOR = 'black'
        self.CURSOR_COLOR = 'blue'

        self.FAKE_WIN_COLOR = 'red'


if __name__ == '__main__':
    desktop = Dims(0, 0, 400, 225)
    ws = Workspace(desktop)
    ws.tile()
    ws.tile()
    # nl = ws.find_leaf_parts()
    # print(nl)
    # print()
    # bu = ws._bottom_up_traverse(nl[-2])
    # for p in bu:
    #     print(p)
    # print(ws.find_neighbors('h', nl[0]))
    print(ws)