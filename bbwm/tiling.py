import abc

try:
    from geometry import Split
except:
    from .geometry import Split

# tiling logic
class TileScheme:
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        pass

    @abc.abstractmethod
    def tile(self, part, new_win=None):
        return

    def manual_tile(self, parts, new_win=None):
        if parts is not None:
            nmt = ManualTilingScheme()
            for p in parts:
                p.assoc_ts = nmt

    @abc.abstractmethod
    def untile(self, part):
        return


class ManualTilingScheme(TileScheme):
    def tile(self, part, new_win=None):
        if new_win is not None:
            if new_win.part is not None:
                # don't retile
                return
            elif part.window is None:
                # add to current partition if it's empty
                part.window = new_win
                new_win.part = part

    def manual_tile(self, parts, new_win=None):
        for p in parts:
            p.assoc_ts = self

    def untile(self, part, new_win=None):
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
            nps = part.split_h(0.67, new_win)
        else:
            if self.tile_count % 2 == 0:
                nps = part.split_h(0.5, new_win)
            else:
                nps = part.split_v(0.5, new_win)
        if nps is not None:
            self.tile_count += 1
            for p in nps:
                p.assoc_ts = self
            return nps[0]

    def untile(self, part, new_win=None):
        self.tile_count = max(0, self.tile_count - 1)


class HorizontalTilingScheme(TileScheme):
    def __init__(self):
        super().__init__()

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
        nps = part._multi_split('h', new_win)
        for p in nps:
            p.assoc_ts = self
        return nps[0]

    def untile(self, part, new_win=None):
        if part.parent is not None:
            pps = part.parent.split
            if pps is not None:
                part.parent.split = Split(pps.d, max(1, pps.r - 1), pps.t)
