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

    def unsplit_h(self, i, r=0.5):
        un_r = 1 / r
        new_w = int(self.w * un_r)
        new_x = self.x + (i - 1) * int(new_w * r)
        return Dims(new_x, self.y, new_w, self.h)

    def unsplit_v(self, i, r=0.5):
        un_r = 1 / r
        new_h = int(self.h * un_r)
        new_y = self.y + (i - 1) * int(new_h * r)
        return Dims(self.x, new_y, self.w, new_h)

    def midpoint(self):
        return self.x + (self.w // 2), self.y + (self.h // 2)

    def distance_to(self, x2, y2):
        # manhattan dist
        x1, y1 = self.midpoint()

        return abs(x1 - x2) + abs(y1 - y2)

    def adjacency_check(self, other, i):
        e_s_1 = self[i]
        e_s_2 = self[i] + self[i + 2] + 1
        e_o_1 = other[i]
        e_o_2 = other[i] + other[i + 2] + 1
        if e_s_1 == e_o_1 and e_s_2 == e_o_2:
            return False
        start_1, end_1 = min(e_s_1, e_s_2), max(e_s_1, e_s_2)
        start_2, end_2 = min(e_o_1, e_o_2), max(e_o_1, e_o_2)
        return (start_1 >= start_2 and start_1 <= end_2) or \
               (end_1 >= start_2 and end_1 <= end_2) or \
               (start_2 >= start_1 and start_2 <= end_1) or \
               (end_2 >= start_1 and end_2 <= end_1)


class Split(namedtuple('Split', ['d', 'r', 'i'])):
    # direction, ratio and index
    # direction can be either
    # h - horizontal
    # v - vertical
    # n - neither
    # ratio is a float between 0 and 1
    __slots__ = ()

    def __str__(self):
        return 'split #{}: (d: {}, r: {:3f})'.format(self.i, self.d, self.r)


# boxing
class Workspace:
    # a workspace is like a super-partition
    def __init__(self, base_dims, tile_scheme=None, first_child=None):
        self.base_dims = base_dims

        if tile_scheme is None:
            tile_scheme = DefaultTilingScheme()
        self.tile_scheme = tile_scheme

        if first_child is None:
            first_child = Partition(self, self.base_dims)
        else:
            first_child.parent = self
            first_child.dims = self.base_dims

        self.children = [first_child]
        self.cur_part = first_child

        # moving around
        self.go_left = lambda: self._move('h', -1)
        self.go_right = lambda: self._move('h', 1)
        self.go_up = lambda: self._move('v', -1)
        self.go_down = lambda: self._move('v', 1)

    def _full_traversal(self, part):
        tor = [part]
        for p in part:
            tor.extend(self._full_traversal(p))
        return tor

    def traverse(self, part=None, filter_fun=None):
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
            tor.extend(self.traverse(p, filter_fun))
        return tor

    def find_neighbors(self, d):
        cp = self.cur_part
        i = 1 if d == 'v' else 0

        # find all partitions that were split in the direction we're looking for
        cands = self.find_splits(d, cp)
        # get all their children
        all_p = []
        for c in cands:
            all_p.extend(self.traverse(c))
        all_p = list(set(all_p))
        # now only do ones that touch..
        fil_p = [p for p in all_p if p.dims.adjacency_check(cp.dims, i)]
        fil_p.append(cp)
        fil_p = list(set(fil_p))

        # sort them
        fil_p.sort(key=lambda p: p.dims[i])
        return fil_p

    def find_splits(self, d, part=None, found=None):
        if found is None:
            found = []
        if part is None:
            return found
        if part.split_past[0] == d:
            found.extend(part.siblings)
        return self.find_splits(d, part.parent, found)

    def tile(self, new_win=None):
        np = self.tile_scheme.tile(self.cur_part, new_win)
        if np is not None:
            self.cur_part = np

    def split_h(self, r=0.5, new_win=None):
        np = self.cur_part.split_h(r, new_win)
        if np is not None:
            self.cur_part = np

    def split_v(self, r=0.5, new_win=None):
        np = self.cur_part.split_v(r, new_win)
        if np is not None:
            self.cur_part = np

    def untile(self):
        cp = self.cur_part
        if cp.parent is None:
            return
        x, y = cp.dims.midpoint()
        where_was_it = cp.parent.delete(cp)
        if where_was_it < 0:
            return
        tree = self.traverse()
        tree.sort(key=lambda p: p.dims.distance_to(x, y))
        self.cur_part = tree[0]

        affected_nodes = self.full_traversal(cp.parent)
        affected_nodes = list(set(affected_nodes))
        # self.undo_split(affected_nodes, cp.split_past, where_was_it)

    def undo_split(self, part_list, split_past, i):
        for p in part_list:
            # if p.split_past[0] is not None
            p._unsplit(split_past, i)

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
        # want closest to something akin to where we're aiming..
        x, y = cp.dims.midpoint()
        x += cp.dims.w * n * (1 - axis)
        y += cp.dims.h * n * axis

        next_ps.sort(key=lambda p: p.dims.distance_to(x, y))
        self.cur_part = next_ps[0]


class Partition:
    def __init__(self, parent, dims, split=None, win=None):
        self.parent = parent
        self.children = []

        self.dims = dims
        if split is None:
            split = Split('n', 1.0, 0)
        self.split = split
        self.window = win

    @property
    def is_empty(self):
        return len(self.children) == 0

    @property
    def siblings(self):
        if self.parent is not None:
            return self.parent.children
        return []

    def __iter__(self):
        if not self.is_empty:
            for b in self.children:
                yield b

    def __str__(self):
        s = 'part {}'.format(self.dims.__str__())
        if self.window is not None:
            s = '{}\n\thas window {}'.format(s, self.window.handle)
        return s

    def delete(self, child):
        if child not in self.children:
            return -1

        where_was_it = self.children.index(child)
        new_me = self.children[1 - where_was_it]

        self.window = new_me.window
        self.children = new_me.children
        # self.dims = new_me.dims
        self.split_past = new_me.split_past
        return where_was_it

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
        p1 = Partition(self, dim1, Split(d, r, 0), self.window)
        # any new window goes into second
        p2 = Partition(self, dim2, Split(d, r, 1), new_win)
        self.children.extend([p1, p2])
        if new_win is None:
            return p1
        return p2

    def split_h(self, r=0.5, new_win=None):
        return self._split('h', r, new_win)

    def split_v(self, r=0.5, new_win=None):
        return self._split('v', r, new_win)

    # def _unsplit(self, split_past, i):
    #     if split_past[0] == 'v':
    #         print('-'*40)
    #         print(self.dims)
    #         self.dims = self.dims.unsplit_v(i, split_past[1])
    #         print(self.dims)
    #     else:
    #         self.dims = self.dims.unsplit_h(i, split_past[1])



class WinNode:
    def __init__(self, dims, handle=None):
        self.handle = handle
        self.dims = dims

    def __str__(self):
        return 'win {} | {}'.format(self.dims.__str__(), self.handle)


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
        if self.tile_count == 0:
            np = part.split_h(0.67, new_win)
        else:
            np = part.split_v(0.5, new_win)
        if np is not None:
            self.tile_count += 1
            return np

    def untile(self, part):
        self.tile_count = max(0, self.tile_count - 1)


# configuration
class Config:
    def __init__(self):
        # inner spacing
        self.INNER_SPACING_X = 8
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
    # ws.tile()
    nl = ws.traverse()
    print(nl)
    print(ws.children[0].children)
    