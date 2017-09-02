from collections import namedtuple
import abc


# geometry
class Dims(namedtuple('Dims', ['x', 'y', 'w', 'h'])):
    __slots__ = ()

    def __str__(self):
        return '@ ({:4d},{:4d}) | w: {:4d} h: {:4d}'.format(self.x, self.y, self.w, self.h)


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


class Partition:
    def __init__(self, parent, dims):
        self.parent = parent
        self.children = []

        self.dims = dims
        self.window = None

    @property
    def is_empty(self):
        return len(self.children) == 0

    def __iter__(self):
        if not self.is_empty:
            for b in self.children:
                yield b
        else:
            yield self

    def split_h(self, r=0.5, new_win=None):
        pass

    def split_v(self, r=0.5, new_win=None):
        pass

    def unsplit(self):
        pass


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
            part.split_h(0.67, new_win)
        else:
            part.split_v(new_win)
        self.tile_count += 1

    def untile(self, part):
        self.tile_count = max(0, self.tile_count - 1)
        part.unsplit()


# configuration
class Config:
    def __init__(self):
        # inner spacing
        self.INNER_SPACING_X = 8
        self.INNER_SPACING_Y = 10

        # colors
        self.BORDER_HIGHLIGHT_COLOR = 'gray'
        self.BORDER_COLOR = 'black'

if __name__ == '__main__':
    desktop = Dims(0, 0, 400, 225)
    ws = Workspace(0, desktop)
