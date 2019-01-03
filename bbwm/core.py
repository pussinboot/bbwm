from .tiling import DefaultTilingScheme
from .geometry import Dims, Split


# boxing
class Workspace:
    # a workspace is like a super-partition
    def __init__(self, base_dims, tile_scheme=None, first_child=None):
        self.base_dims = base_dims

        if tile_scheme is None:

            tile_scheme = DefaultTilingScheme(base_dims.w > base_dims.h)
            # tile_scheme = HorizontalTilingScheme()
        self.tile_scheme = tile_scheme

        if first_child is None:
            first_child = Partition(None, self.base_dims, ts=self.tile_scheme)
        else:
            first_child.parent = self
            first_child.dims = self.base_dims
            first_child.assoc_ts = self.tile_scheme

        self.children = [first_child]
        self.cur_part = first_child

        # for pseudo-partitions
        self.parent = None
        self.split = None
        self.assoc_ts = self.tile_scheme

        # moving around
        self.go_left = lambda: self._move('h', -1)
        self.go_right = lambda: self._move('h', 1)
        self.go_up = lambda: self._move('v', -1)
        self.go_down = lambda: self._move('v', 1)

        self.swap_left = lambda: self._swap('h', -1)
        self.swap_right = lambda: self._swap('h', 1)
        self.swap_up = lambda: self._swap('v', -1)
        self.swap_down = lambda: self._swap('v', 1)

    def _str_help(self, part, prefix=""):
        if part == self.cur_part:
            tor = ["{}{} ***".format(prefix, part.__str__())]
        else:
            tor = ["{}{}".format(prefix, part.__str__())]
        pref = "\t{}".format(prefix)
        for p in part:
            tor.extend(self._str_help(p, pref))
        return tor

    def __str__(self):
        top_line = '-' * 15
        all_str = self._str_help(self.children[0])
        return '{}\n{}'.format(top_line, "\n".join(all_str))

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

    def _bottom_up_traverse(self, part, stopping_condition=None):
        if stopping_condition is None:
            def stopping_condition(p):
                return not isinstance(p, Partition)

        tor = [part]
        if part.parent is not None and not stopping_condition(part):
            tor.extend(self._bottom_up_traverse(part.parent, stopping_condition))
        return tor

    def find_leaf_parts(self, root=None):
        if root is None:
            root = self
        return self._traverse(root, lambda p: p.is_empty)

    def find_all_splits(self, root=None):
        if root is None:
            root = self
        return self._traverse(root, lambda p: p.split is not None)

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

    def find_move(self, d, n):
        axis = 1 if d == 'v' else 0
        cp = self.cur_part

        n_ps = self.find_neighbors(d)
        i = n_ps.index(cp)
        new_i = i + n

        if new_i < 0 or new_i >= len(n_ps):
            # mono tiling
            bot_up = self._bottom_up_traverse(cp, lambda p: p.split is not None and p.split.d == 'n')
            if len(bot_up) and bot_up[-1].split is not None:
                if bot_up[-1].split.d == 'n':
                    n_ps = self._traverse(bot_up[-1], lambda p: p.is_empty and p != cp)
                    if len(n_ps):
                        return n_ps[0]
            return  # no wraparound..
        # now sort by distance
        next_ps = n_ps[new_i::n]
        # want closest to corner
        x = cp.dims[0]  # + (1 + n) // 2 * cp.dims[2]
        # xor to add height
        y = cp.dims[1] + cp.dims[3] * (bool((1 - n) // 2) != bool(axis))

        next_ps.sort(key=lambda p: p.dims.distance_to(x, y))
        return next_ps[0]

    def _move(self, d, n):
        next_part = self.find_move(d, n)
        if next_part is not None:
            self.cur_part = next_part

    def _swap_win(self, p1, p2):
        if p1.window is not None:
            p1.window = p2.window if p2 is not None else None
            p1.window.part = p2

    def _swap(self, d, n):
        next_part = self.find_move(d, n)
        if next_part is not None:
            nw, cw = next_part.window, self.cur_part.window
            next_part.window = cw
            self.cur_part.window = nw
            if nw is not None:
                nw.part = self.cur_part
            if cw is not None:
                cw.part = next_part
            self.cur_part = next_part

    def _split(self, d, r=0.5, new_win=None):
        # mono tiling is buggy so no you cant split further sorry
        # fixing this will require properly tackling same issue
        # that's plaguing switching tiling schemes
        # (some way to go up and down making extra partitions as needed)
        # ((this is too ugly lol))
        if self.cur_part.parent is not None and self.cur_part.parent.split is not None:
            if self.cur_part.parent.split.d == 'n':
                return

        if d == 'h':
            nps = self.cur_part.split_h(r, new_win)
        elif d == 'v':
            nps = self.cur_part.split_v(r, new_win)
        else:
            nps = self.cur_part.split_n(r, new_win)

        if nps is not None:
            self.cur_part = nps[0]
        self.tile_scheme.manual_tile(nps, new_win)

    def tile(self, new_win=None):
        np = self.cur_part.assoc_ts.tile(self.cur_part, new_win)
        if np is not None:
            self.cur_part = np
            return True

    def rotate(self, part=None):
        if part is None:
            part = self.cur_part
        if part.parent is None:
            return
        pp = part.parent
        if pp.split is None:
            return
        # neither split dirs dont rotate
        if pp.split.d == 'n':
            return
        new_d = 'h' if pp.split.d == 'v' else 'v'
        new_c = (pp.split.c + 1) % 2
        new_r = 1 - pp.split.r if new_c == 0 else pp.split.r
        pp.split = Split(new_d, new_r, pp.split.t, new_c)

        aff_parts = self._traverse()

        for p in aff_parts:
            p.resize_from_parent()

    def resplit(self, part, new_r):
        if part.split is None:
            return
        part.split = Split(part.split.d, new_r)

        aff_parts = self._traverse()

        for p in aff_parts:
            p.resize_from_parent()

    def untile(self, part=None):
        if part is None:
            cp = self.cur_part
        else:
            cp = part
        if cp.parent is None:
            return cp
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

        if cp == self.cur_part:
            # if the partition we untiled was current
            # reassign to closest leaf partition
            if next_cur.is_empty:
                self.cur_part = next_cur
            else:
                self.cur_part = self.find_leaf_parts(next_cur)[0]

        cp.assoc_ts.untile(cp)

        # now recompute all dims because this doesnt work...
        aff_parts = self._traverse()

        for p in aff_parts:
            p.resize_from_parent()

        return cp


class Partition:
    def __init__(self, parent, dims, index=0, win=None, ts=None):
        self.parent = parent
        self.children = []

        self.dims = dims
        self.index = index
        self.split = None
        self.window = win
        if self.window is not None:
            self.window.part = self
        self.assoc_ts = ts  # associated tile-scheme

    @property
    def is_empty(self):
        return len(self.children) == 0

    @property
    def siblings(self):
        if self.parent is not None:
            return self.parent.children
        return []

    @property
    def split_siblings(self):
        return [c for c in self.siblings if c.split is not None]

    def __iter__(self):
        for b in self.children:
            yield b

    def __str__(self):
        s = 'part (#{}) {}'.format(self.index, self.dims.__str__())
        if self.split is not None:
            s = '{} | {}'.format(s, self.split.__str__())
        if self.window is not None:
            s = '{} | win : {}'.format(s, self.window.hwnd)
        if self.assoc_ts is not None:
            s = '{} | tile-scheme : {}'.format(s, self.assoc_ts.__class__.__name__)
        return s

    def _traverse(self, part=None):
        if part is None:
            part = self
        tor = [part]
        for p in part:
            tor.extend(self._traverse(p))
        return tor

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
        # need to check split type..
        split = self.parent.split
        if split.t is None:
            self.dims = self.parent.dims.resize(split.d, split.r, self.index)
        elif split.t == 'equal':
            n = len(self.parent.children)
            self.dims = self.parent.dims.resize_n(split.d, n, self.index)

    def _split(self, d, r, new_win):
        if d == 'h':
            sf = self.dims.split_h
        elif d == 'v':
            sf = self.dims.split_v
        else:
            sf = self.dims.split_n

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
            return p1, p2
        return p2, p1

    def _multi_split(self, d, new_win):
        if self.parent is None:
            return self._split(d, 0.5, new_win)
        if d == 'h':
            sf = self.parent.dims.split_h_n
        elif d == 'v':
            sf = self.parent.dims.split_v_n
        else:
            # adding tabs?
            return
        n = len(self.parent.children) + 1
        new_dims = sf(n)

        for i, part in enumerate(self.parent.children):
            part.dims = new_dims[i]

        new_part = Partition(self.parent, new_dims[-1], n - 1, new_win)
        self.parent.children.append(new_part)
        self.parent.split = Split(d, n, 'equal')

        aff_parts = self._traverse(self.parent)
        for aff_p in aff_parts:
            aff_p.resize_from_parent()

        # if new_win is not None:
        return [new_part]
        # otherwise return last non_empty leaf node

    def split_h(self, r=0.5, new_win=None):
        return self._split('h', r, new_win)

    def split_v(self, r=0.5, new_win=None):
        return self._split('v', r, new_win)

    def split_n(self, r=0, new_win=None):
        return self._split('n', r, new_win)


# displays
def calc_display_nav(disp_dims):

    dist_funs = {
        'u': lambda d, o: d.y - o.b_y,
        'd': lambda d, o: o.y - d.b_y,
        'l': lambda d, o: d.x - o.r_x,
        'r': lambda d, o: o.x - d.r_x
    }

    disp_nav = []

    for i, disp in enumerate(disp_dims):
        o_disps = [(j, d) for j, d in enumerate(disp_dims) if i != j]
        d_to_nav = {'u': None, 'd': None, 'l': None, 'r': None}
        for dx in d_to_nav:
            o_dists = [(j, dist_funs[dx](disp, o_d)) for (j, o_d) in o_disps]
            o_dists = [dist for dist in o_dists if dist[1] >= 0]
            o_dists.sort(key=lambda dist: dist[1])
            if len(o_dists):
                d_to_nav[dx] = o_dists[0][0]

        disp_nav.append(d_to_nav)

    return disp_nav


# configuration
class Config:
    def __init__(self):

        # left, top, right, bottom
        self.BORDER_OFFSETS = [25, 30, 25, 20]
        self.OFF_SCREEN = max(self.BORDER_OFFSETS) + 50

        self.MIN_RATIO = 0.05
        self.N_KB_RATIOS = 6

        # inner spacing
        self.INNER_SPACING_X = 10
        self.INNER_SPACING_Y = 10

        # sizes
        self.CURSOR_SIZE = 20

        # workspaces
        self.NO_WORKSPACES = 3

        # gui stuff

        self.FRAME_DUR = 10
        # how many frames to fade in/out
        self.FADE_N = 7
        self.CLEAR_TIMEOUT = 20

        self.DEFAULT_OPACITY = 0.77
        self.PRETTY_WINS = False
        self.FONT = ('IBM 3161', 14)

        # colors
        self.TRANSPARENT_COLOR = '#0DEAD0'

        self.BORDER_HIGHLIGHT_COLOR = 'gray'
        self.BORDER_COLOR = 'black'

        self.SELECTION_COLOR = '#222222'

        self.CURSOR_COLOR = 'blue'
        self.FAKE_WIN_COLOR = 'red'
