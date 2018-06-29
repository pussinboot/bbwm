import tkinter as tk


class BBDraw:
    def __init__(self, root, monitor_bbox, c):
        self.c = c  # config

        self.m_bbox = monitor_bbox

        self.root = root
        self.root.title('__bbwm__')
        self.root.attributes('-alpha', self.c.DEFAULT_OPACITY)
        self.root.wm_attributes("-topmost", True)
        self.root.wm_attributes("-transparentcolor", self.c.TRANSPARENT_COLOR)
        self.root.overrideredirect(True)

        self.max_w, self.max_h = self.m_bbox[2] - self.m_bbox[0], self.m_bbox[3] - self.m_bbox[1]
        w, h = self.max_w + 2 * c.OFF_SCREEN, self.max_h + 2 * c.OFF_SCREEN
        x, y = self.m_bbox[0] - c.OFF_SCREEN, self.m_bbox[1] - c.OFF_SCREEN
        self.root.geometry('%dx%d+%d+%d' % (w, h, x, y))
        self._x_o, self._y_o = -x, -y

        self.part_width = max(min(self.c.INNER_SPACING_X, self.c.INNER_SPACING_Y) - 2, 2)

        self.canvas = tk.Canvas(root, width=w, height=h, bg=self.c.TRANSPARENT_COLOR, highlightthickness=0)
        self.canvas.pack()

        # for fading
        self._fade_dt = 0
        self._fade_to = 0

        # for resizing partitions

        self._draw_job = None
        self._drag_data = {"x": 0, "y": 0, "item": None, 'dir': None}

        self.line_to_part = {}

        self._last_split = None
        self._last_part = None

        self.resplit_fun = None
        self.unfocus_fun = None

        for d in ['h', 'v']:
            self.canvas.tag_bind(d, "<ButtonPress-1>", self.drag_begin)
            self.canvas.tag_bind(d, "<ButtonRelease-1>", self.drag_end)
            self.canvas.tag_bind(d, "<B1-Motion>", self.drag)

        # for menu stuff

        self._click_to_fun = []
        self._button_binds = []

    # -- helper calcs -- #

    def _dims_to_canvas_coords(self, dims):
        x, y, w, h = dims.x, dims.y, dims.w, dims.h
        x, y = x + self._x_o, y + self._y_o
        rx = x + w
        by = y + h
        return x, y, rx, by

    def _calc_split_line(self, part):
        dims, split = part.dims, part.split
        d_i = int(split.d == 'h')
        is_x, is_y = self.c.INNER_SPACING_X, self.c.INNER_SPACING_Y

        x, y, w, h = dims.x, dims.y, dims.w, dims.h
        x, y = x + self._x_o + is_x / 2, y + self._y_o + is_y / 2
        w, h = w - is_x, h - is_y

        l_thicc = [is_x, is_y][d_i] * 2

        rx = x + int((w) * split.r) * (d_i) + (w) * (1 - d_i)
        by = y + int((h) * split.r) * (1 - d_i) + (h) * (d_i)

        # still not quite...
        if d_i:
            x = rx  # + 1
        else:
            y = by  # + 1

        return x, y, rx, by, l_thicc

    def _calc_mon_offset(self):
        # some sort of max bbox scaling probably better

        x, y = self.root.winfo_pointerx(), self.root.winfo_pointery()
        x, y = x + self._x_o, y + self._y_o
        # x & y are relative top top left corner of all monitors
        # so that midpoint will be where your mouse is
        x, y = x - self.max_w // 20, y - self.max_h // 20
        return x, y

    # -- helper funs -- #

    def clear_screen(self):
        self.canvas.delete('all')
        del self.line_to_part
        self.line_to_part = {}

        self._last_split = None
        self._last_part = None

    def lost_focus(self, e):
        self.reset_menu()
        self.fade_out()
        self.root.unbind('<FocusOut>')
        if self.unfocus_fun is not None:
            self.unfocus_fun()

    def _menu_help(self, fun):
        def new_fun(e):
            fun()
            self.fade_out()
        return new_fun

    def reset_menu(self, tag_to_fun=[]):

        for kb in self._button_binds:
            self.canvas.unbind(kb)
        self._button_binds = []

        for tag in self._click_to_fun:
            self.canvas.tag_unbind(tag, "<ButtonPress-1>")

        self._click_to_fun = []
        for (tag, fun) in tag_to_fun:
            self._click_to_fun.append(tag)
            self.canvas.tag_bind(tag, "<ButtonPress-1>", self._menu_help(fun))

    # -- basic draws -- #

    def write_centered_text(self, x1, x2, y1, y2, text, tags=[]):
        self.canvas.create_text((x1 + x2) // 2, (y1 + y2) // 2,
                                fill=self.c.BORDER_HIGHLIGHT_COLOR,
                                font=self.c.FONT,
                                text=text, tags=tags)

    def draw_part(self, dims, current, single=False):
        outline = self.c.BORDER_HIGHLIGHT_COLOR if current else self.c.BORDER_COLOR

        rect = self.canvas.create_rectangle(*self._dims_to_canvas_coords(dims),
                                            outline=outline, width=self.part_width)

        if single:
            if self._last_part is not None:
                self.canvas.delete(self._last_part)
            self._last_part = rect

    def draw_split(self, part, single=False):
        split = part.split
        if split.t is not None:  # for now we will not draw equal spaced splits
            return
        x, y, rx, by, w = self._calc_split_line(part)

        new_line = self.canvas.create_line(x, y, rx, by,
                                           fill=self.c.BORDER_HIGHLIGHT_COLOR,
                                           activefill=self.c.BORDER_COLOR,
                                           width=w,
                                           tags=(split.d if split.t is None else '')
                                           )
        if single:
            if self._last_split is not None:
                self.canvas.delete(self._last_split)
            self._last_split = new_line
        self.line_to_part[new_line] = part

    def draw_monitor(self, dims, x_o, y_o, text=''):

        # translate n scale
        x1 = x_o + (dims.x - self.m_bbox[0]) // 10
        y1 = y_o + (dims.y - self.m_bbox[1]) // 10

        x2 = x1 + dims.w // 10
        y2 = y1 + dims.h // 10

        self.canvas.create_rectangle(x1, y1, x2, y2,
                                     outline=self.c.BORDER_HIGHLIGHT_COLOR,
                                     fill=self.c.BORDER_COLOR,
                                     width=2)
        self.write_centered_text(x1, x2, y1, y2, text)

    def draw_win(self, dims, x_o, y_o, i, active=False):
        x1 = x_o + (dims.x - self.m_bbox[0]) // 10
        y1 = y_o + (dims.y - self.m_bbox[1]) // 10

        x2 = x1 + dims.w // 10
        y2 = y1 + dims.h // 10

        self.canvas.create_rectangle(x1 + 1, y1 + 1, x2 - 2, y2 - 2,
                                     outline=self.c.BORDER_HIGHLIGHT_COLOR,
                                     fill=self.c.BORDER_HIGHLIGHT_COLOR if active else self.c.SELECTION_COLOR)
        self.write_centered_text(x1, x2, y1, y2, i)

    # -- splits -- #

    def move_split(self, part, the_line=None):
        if the_line is None:
            the_line = self._last_split
        if the_line is None:
            return
        x, y, rx, by, _ = self._calc_split_line(part)
        self.canvas.coords(the_line, x, y, rx, by)

    def split_menu(self, split_funs):
        for s_kb, s_fun in split_funs:
            self.canvas.bind(s_kb, s_fun)
            self._button_binds.append(s_kb)

        self.canvas.bind('<Escape>', self.lost_focus)
        self._button_binds.append('<Escape>')

        self.canvas.focus_force()
        self.root.bind('<FocusOut>', self.lost_focus)

    # -- tilescheme menu -- #

    def draw_menu(self, tags_to_funs):
        x, y = self.root.winfo_pointerx(), self.root.winfo_pointery()
        x, y = x + self._x_o, y + self._y_o
        w = self.part_width // 2

        dxy = [[-1, -1], [1, -1],
               [-1, 1], [1, 1]]

        for i in range(4):
            dxdy = dxy[i]
            x2, y2 = x + 75 * dxdy[0], y + 75 * dxdy[1]
            tag = tags_to_funs[i][0]
            self.canvas.create_rectangle(min(x, x2), min(y, y2),
                                         max(x, x2), max(y, y2),
                                         outline=self.c.BORDER_HIGHLIGHT_COLOR,
                                         fill=self.c.BORDER_COLOR,
                                         width=w,
                                         tags=(tag))
            self.write_centered_text(x, x2, y, y2, tag, tags=(tag))

        self.reset_menu(tags_to_funs)
        self.root.bind('<FocusOut>', self.lost_focus)

    def draw_menu_list(self, menu_list, disp_list, x_o, y_o):
        for m_kb, _, m_fun in menu_list:
            if len(str(m_kb)) == 1:
                self.canvas.bind(m_kb, m_fun)
                self._button_binds.append(m_kb)

        for d_kb, d_fun in disp_list:
            self.canvas.bind(d_kb, d_fun)
            self._button_binds.append(d_kb)

        self.canvas.bind('<Escape>', self.lost_focus)
        self._button_binds.append('<Escape>')

        self.canvas.focus_force()
        self.root.bind('<FocusOut>', self.lost_focus)

    # -- fading -- #

    def _fade(self, delay, _finally=None):
        _to = self._fade_to
        step = self._fade_dt

        progress = self.root.attributes('-alpha')
        progress += step
        self.root.attributes('-alpha', progress)

        if (step < 0 and progress <= _to) or (step >= 0 and progress >= _to):
            if _finally is not None:
                _finally()
            self._draw_job = None
            return
        self._draw_job = self.root.after(delay, lambda: self._fade(delay, _finally))

    def fade_out(self, and_then=None):
        if self._draw_job is not None:
            self.root.after_cancel(self._draw_job)

        self._fade_dt = -self.c.DEFAULT_OPACITY / 5
        self._fade_to = 0

        delay = int(self.c.CLEAR_TIMEOUT / 5)

        self._fade(delay, and_then)

    def fade_in(self, and_then=None):

        self._fade_to = self.c.DEFAULT_OPACITY
        self._fade_dt = self._fade_to / 5

        delay = int(self.c.CLEAR_TIMEOUT / 5)

        self._fade(delay, and_then)

    def fade_out_later(self):
        self._draw_job = self.root.after(self.c.CLEAR_TIMEOUT, self.fade_out)

    # -- dragging -- #

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
            self.resplit_fun(assoc_part, new_r, the_line != self._last_split)

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
