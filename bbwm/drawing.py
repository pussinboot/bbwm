import tkinter as tk


class BBDraw:
    # i guess this is per monitor -.-
    def __init__(self, root, base_dims, c):
        self.c = c  # config

        self.root = root
        self.root.title('bbwm')
        self.root.attributes('-alpha', self.c.DEFAULT_OPACITY)
        root.wm_attributes("-topmost", True)
        root.wm_attributes("-transparentcolor", self.c.TRANSPARENT_COLOR)
        root.overrideredirect(True)

        self.width, self.height = base_dims.w, base_dims.h
        w, h = self.width + 2 * c.OFF_SCREEN, self.height + 2 * c.OFF_SCREEN
        x, y = -c.OFF_SCREEN, -c.OFF_SCREEN
        self.root.geometry('%dx%d+%d+%d' % (w, h, x, y))

        self.canvas = tk.Canvas(root, width=w, height=h, bg=self.c.TRANSPARENT_COLOR)
        self.canvas.pack()

        # for resizing partitions

        self._draw_job = None
        self._drag_data = {"x": 0, "y": 0, "item": None, 'dir': None}

        self.line_to_part = {}
        self.resplit_fun = None

        for d in ['h', 'v']:
            self.canvas.tag_bind(d, "<ButtonPress-1>", self.drag_begin)
            self.canvas.tag_bind(d, "<ButtonRelease-1>", self.drag_end)
            self.canvas.tag_bind(d, "<B1-Motion>", self.drag)

        # for menu stuff

        self._click_to_fun = {}

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
        if split.t is not None:  # for now we will not draw equal spaced splits
            return
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
                   tags=(split.d if split.t is None else '')
        )

        self.line_to_part[new_line] = part

    def draw_menu(self):
        x, y = self.root.winfo_pointerx(), self.root.winfo_pointery()
        x, y = x + self.c.OFF_SCREEN, y + self.c.OFF_SCREEN

        dxy = [[-1, -1], [1, -1],
               [-1,  1], [1,  1]]
        tags_to_funs = [
            ('ul', lambda e: print('up left')),
            ('ur', lambda e: print('up right')),
            ('dl', lambda e: print('down left')),
            ('dr', lambda e: print('down right')),
        ]

        for i in range(4):
            dxdy = dxy[i]
            x2, y2 = x + 75 * dxdy[0], y + 75 * dxdy[1]

            self.canvas.create_rectangle(min(x, x2), min(y, y2),
                                         max(x, x2), max(y, y2),
                                         outline=self.c.BORDER_HIGHLIGHT_COLOR,
                                         fill=self.c.BORDER_COLOR,
                                         tags=(tags_to_funs[i][0]))

        self.reset_menu(tags_to_funs)

    def reset_menu(self, tag_to_fun=[]):
        for tag in self._click_to_fun:
            self.canvas.tag_unbind(tag, "<ButtonPress-1>")

        self._click_to_fun = []
        for (tag, fun) in tag_to_fun:
            self._click_to_fun.append(tag)
            self.canvas.tag_bind(tag, "<ButtonPress-1>", fun)

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

    def fade_in(self, also_fade_out=False):
        if self._draw_job is not None:
            self.root.after_cancel(self._draw_job)
        _to = self.c.DEFAULT_OPACITY
        delay = self.c.CLEAR_TIMEOUT / 5
        step = _to / 5
        delay = int(delay)
        if also_fade_out:
            self._fade(_to, step, delay, lambda: self.root.after(self.c.CLEAR_TIMEOUT, self.fade_out))
        else:
            self._fade(_to, step, delay)

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
