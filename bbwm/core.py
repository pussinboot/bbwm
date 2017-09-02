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


# boxing
class Workspace:
    def __init__(self, index, base_dims, tile_scheme=None):
        self.index = index
        self.base_dims = base_dims

        if tile_scheme is None:
            tile_scheme = DefaultTilingScheme()
        self.tile_scheme = tile_scheme

        self.partitions = [Partition(None, self.base_dims)]
        self.cur_part = self.partitions[0]

        # moving around
        self.go_left = lambda: self._move('h', -1)
        self.go_right = lambda: self._move('h', 1)
        self.go_up = lambda: self._move('v', -1)
        self.go_down = lambda: self._move('v', 1)

    def traverse(self, part=None):
        if part is None:
            part = self.partitions[0]
        tor = []
        for p in part:
            if p.is_empty:
                tor.append(p)
            else:
                tor.extend(self.traverse(p))
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
        if part.split_dir == d:
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
        tree = self.traverse(cp.parent)
        if cp not in tree:
            return
        cur_i = tree.index(cp)
        cp.parent.delete(cp)
        if cp.parent.is_empty:
            self.cur_part = cp.parent
        else:
            del tree[cur_i]
            self.cur_part = tree[min(len(tree) - 1, cur_i)]

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
    def __init__(self, parent, dims, split_dir=None, win=None):
        self.parent = parent
        self.children = []

        self.dims = dims
        self.split_dir = split_dir
        self.window = win

    @property
    def is_empty(self):
        return len(self.children) == 0

    @property
    def siblings(self):
        return self.parent.children

    def __iter__(self):
        if not self.is_empty:
            for b in self.children:
                yield b
        else:
            yield self

    def __str__(self):
        s = 'part {}'.format(self.dims.__str__())
        if self.window is not None:
            s = '{}\n\thas window {}'.format(s, self.window.handle)
        if self.split_dir is not None:
            s = '{}\n\twas split in {} dir'.format(s, self.split_dir)
        return s

    def delete(self, child):
        if child not in self.children:
            return
        self.children.remove(child)
        if self.is_empty:
            return
        if self.parent is None:
            return
        # replace urself with your child
        if len(self.children) == 1:
            my_ind = self.parent.children.index(self)
            self.parent.children[my_ind] = self.children[0]


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
        p1 = Partition(self, dim1, d, self.window)
        # any new window goes into second
        p2 = Partition(self, dim2, d, new_win)
        self.children.extend([p1, p2])
        if new_win is None:
            return p1
        return p2

    def split_h(self, r=0.5, new_win=None):
        return self._split('h', r, new_win)

    def split_v(self, r=0.5, new_win=None):
        return self._split('v', r, new_win)


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
        part.unsplit()


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
    ws = Workspace(0, desktop)
    desktop.check_touching(Dims(1,1,1,1), 'h')
