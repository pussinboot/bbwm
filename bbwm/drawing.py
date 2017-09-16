import tkinter as tk


class TestDraw:
    def __init__(self, root, base_dims, config):
        WIDTH, HEIGHT = base_dims.w, base_dims.h

        self.c = config

        self.root = root
        self.root.title('bbwm test')

        self.canvas = tk.Canvas(self.root, width=WIDTH, height=HEIGHT, bg="#444")
        self.canvas.pack()

        self.cursor = None

        self.root.protocol('WM_DELETE_WINDOW', self.kill)

    def get_bbox(self, dims):
        x, y, w, h = dims.x, dims.y, dims.w, dims.h
        lx, rx = x + self.c.INNER_SPACING_X, x + w - self.c.INNER_SPACING_X
        ty, by = y + self.c.INNER_SPACING_Y, y + h - self.c.INNER_SPACING_Y
        return lx, ty, rx, by

    def draw_border(self, dims, highlight=False):
        if highlight:
            outline = self.c.BORDER_HIGHLIGHT_COLOR
        else:
            outline = self.c.BORDER_COLOR

        w = max(min(self.c.INNER_SPACING_X, self.c.INNER_SPACING_Y) - 2, 2)
        self.canvas.create_rectangle(self.get_bbox(dims), outline=outline, width=w)

    def draw_fill(self, dims):
        self.canvas.create_rectangle(self.get_bbox(dims), fill=self.c.FAKE_WIN_COLOR)

    def draw_cursor(self, dims):
        cx, cy = dims.midpoint()
        r = self.c.CURSOR_SIZE
        if self.cursor is None:
            color = self.c.CURSOR_COLOR
            self.cursor = self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color)
        else:
            self.canvas.coords(self.cursor, cx - r, cy - r, cx + r, cy + r)

    def clear(self):
        self.canvas.delete('all')
        self.cursor = None

    def kill(self):
        self.root.destroy()


class BBDraw:
    # i guess this is per monitor -.-
    def __init__(self, root, base_dims, c):
        self.c = c  # config

        self.root = root
        self.root.title('bbwm')
        self.root.attributes('-alpha', self.c.DEFAULT_OPACITY)

        self.width, self.height = base_dims.w, base_dims.h
        w, h = self.width + 2 * c.OFF_SCREEN, self.height + 2 * c.OFF_SCREEN
        x, y = -c.OFF_SCREEN, -c.OFF_SCREEN
        self.root.geometry('%dx%d+%d+%d' % (w, h, x, y))

        self.canvas = tk.Canvas(root, width=w, height=h, bg="#0DEAD0")
        self.canvas.pack()

        self._draw_job = None
        self._drag_data = {"x": 0, "y": 0, "item": None, 'dir': None}

        self.line_to_part = {}
        self.resplit_fun = None

        for d in ['h', 'v']:
            self.canvas.tag_bind(d, "<ButtonPress-1>", self.drag_begin)
            self.canvas.tag_bind(d, "<ButtonRelease-1>", self.drag_end)
            self.canvas.tag_bind(d, "<B1-Motion>", self.drag)

    def _dims_to_canvas_coords(self, dims):
        x, y, w, h = dims.x, dims.y, dims.w, dims.h
        x, y = x + self.c.OFF_SCREEN, y + self.c.OFF_SCREEN
        rx = x + w
        by = y + h
        return x, y, rx, by

    def draw_border(self, dims, current):
        outline = self.c.BORDER_HIGHLIGHT_COLOR if current else self.c.BORDER_COLOR
        w = max(min(self.c.INNER_SPACING_X, self.c.INNER_SPACING_Y) - 2, 2)

        self.canvas.create_rectangle(*self._dims_to_canvas_coords(dims), outline=outline, width=w)

    def rdy_to_split(self):
        self.root.attributes('-alpha', self.c.DEFAULT_OPACITY)

    def draw_split(self, part):
        dims, split = part.dims, part.split
        d_i = int(split.d == 'h')
        is_x, is_y = self.c.INNER_SPACING_X, self.c.INNER_SPACING_Y
        
        x, y, w, h = dims.x, dims.y, dims.w, dims.h
        x, y = x + self.c.OFF_SCREEN + is_x / 2, y + self.c.OFF_SCREEN + is_y / 2
        w, h = w - is_x, h - is_y

        line_width = [is_x, is_y][d_i]

        rx = x + int((w) * split.r) * (d_i) + (w) * (1 - d_i)
        by = y + int((h) * split.r) * (1 - d_i) + (h) * (d_i)

        if d_i:
            x = rx
        else:
            y = by

        new_line = self.canvas.create_line(x, y, rx, by,
                   fill=self.c.BORDER_COLOR,
                   activefill=self.c.BORDER_HIGHLIGHT_COLOR,
                   width=line_width,
                   tags=split.d
                   )

        self.line_to_part[new_line] = part

    def clear_screen(self):
        self.canvas.delete('all')
        del self.line_to_part
        self.line_to_part = {}

    def _fade(self, _to, step, delay, _finally=None):
        progress = self.root.attributes('-alpha')
        progress += step
        self.root.attributes('-alpha', progress)
        if (step < 0 and progress <= _to) or (step >= 0 and progress >= _to):
            if _finally is not None:
                self._draw_job = _finally()
            return
        self._draw_job = self.root.after(delay, lambda: self._fade(_to, step, delay, _finally))

    def fade_out(self):
        _from, _to = self.c.DEFAULT_OPACITY, 0
        delay = self.c.CLEAR_TIMEOUT / 5
        step = -_from / 5
        delay = int(delay)
        self._fade(_to, step, delay)

    def fade_in(self):
        if self._draw_job is not None:
            self.root.after_cancel(self._draw_job)
        _from, _to = 0, self.c.DEFAULT_OPACITY
        delay = self.c.CLEAR_TIMEOUT / 5
        step = _to / 5
        delay = int(delay)
        self._fade(_from, _to, step, delay, lambda: self.root.after(self.c.CLEAR_TIMEOUT, self.fade_out))

    def fade_immediately(self):
        if self._draw_job is not None:
            self.root.after_cancel(self._draw_job)
        self.root.attributes('-alpha', self.c.DEFAULT_OPACITY)
        self.root.after(self.c.CLEAR_TIMEOUT, self.fade_out)

    def drag_begin(self, event):
        # record the item and its location
        item = self.canvas.find_closest(self.canvas.canvasx(event.x), self.canvas.canvasy(event.y), halo=5)[0]
        self._drag_data["item"] = item
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
        self._drag_data["dir"] = self.canvas.gettags(item)[0]

        self.canvas.tag_raise(item)

    def drag_end(self, event):
        the_line = self._drag_data["item"]
        if (the_line is None) or (the_line not in self.line_to_part):
            return
        if self.resplit_fun is not None:
            assoc_part = self.line_to_part[the_line]
            lx, ty, rx, by = self._dims_to_canvas_coords(assoc_part.dims)
            # compute new split ratio
            if self._drag_data["dir"] == 'h':
                new_r = (self._drag_data["x"] - lx) / (rx - lx)
            elif self._drag_data["dir"] == 'v':
                new_r = (self._drag_data["y"] - ty) / (by - ty)
            else:
                return
            new_r = max(min(new_r, 1 - self.c.MIN_RATIO), self.c.MIN_RATIO)
            # update it with the fun
            self.resplit_fun(assoc_part, new_r)

        self._drag_data = {"x": 0, "y": 0, "item": None, 'dir': None}

    def drag(self, event):
        d = self._drag_data["dir"]
        the_line = self._drag_data["item"]
        if the_line not in self.line_to_part:
            return
        assoc_part = self.line_to_part[the_line]
        lx, ty, rx, by = self._dims_to_canvas_coords(assoc_part.dims)

        if d == 'h':
            if event.x < lx:
                event.x = lx
            elif event.x > rx:
                event.x = rx
            delta_x = event.x - self._drag_data["x"]
            delta_y = 0
            self._drag_data["x"] = event.x
        elif d == 'v':
            if event.y < ty:
                event.y = ty
            elif event.y > by:
                event.y = by
            delta_x = 0
            delta_y = event.y - self._drag_data["y"]
            self._drag_data["y"] = event.y
        else:
            return

        self.canvas.move(the_line, delta_x, delta_y)

