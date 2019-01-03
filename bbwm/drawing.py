import tkinter as tk
import math

from queue import Queue


class BBDraw:
    def __init__(self, root, monitor_bbox, c):
        self.c = c  # config

        self.m_bbox = monitor_bbox

        self.root = root
        self.root.title('__bbwm__')
        self.root.attributes('-alpha', self.c.DEFAULT_OPACITY)
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

        self._job_queue = Queue()

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
        # x, y = x + self._x_o + is_x / 2, y + self._y_o + is_y / 2
        x, y = x + self._x_o, y + self._y_o
        # w, h = w - is_x, h - is_y

        l_thicc = [is_x, is_y][d_i]

        rx = x + math.floor((w) * split.r) * (d_i) + (w) * (1 - d_i)
        by = y + math.floor((h) * split.r) * (1 - d_i) + (h) * (d_i)

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
        self.fo_draw()
        self.root.unbind('<FocusOut>')
        if self.unfocus_fun is not None:
            self.unfocus_fun()

    def _menu_help(self, fun):
        def new_fun(e):
            fun()
            self.fo_draw()
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

    def draw_split(self, part, single=False, inactive=True):
        split = part.split
        if split.t is not None:  # for now we will not draw equal spaced splits
            return
        x, y, rx, by, w = self._calc_split_line(part)

        fill = self.c.BORDER_HIGHLIGHT_COLOR if inactive else self.c.SELECTION_COLOR

        new_line = self.canvas.create_line(x, y, rx, by,
                                           fill=fill,
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

    def draw_menu_list(self, menu_list, disp_list, x_o, y_o, cur_i):
        cl = CanvasList(self.c, self.canvas, cur_i)

        x1 = x_o
        x2 = x_o + self.max_w // 10
        n_y = y_o + self.max_h // 10 + 5

        for i, (m_kb, m_title, m_fun) in enumerate(menu_list):
            if len(str(m_kb)) == 1:
                self.canvas.bind(m_kb, m_fun)
                self._button_binds.append(m_kb)

            fill = self.c.SELECTION_COLOR if i == cur_i else self.c.BORDER_COLOR
            new_row = self.canvas.create_rectangle(x1, n_y, x2, n_y + 23,
                                                   outline=self.c.BORDER_HIGHLIGHT_COLOR,
                                                   fill=fill,
                                                   width=1, tags=('list_row'))
            self.write_centered_text(x1, x1 + 25, n_y, n_y + 23, m_kb)
            t_text = m_title
            if len(t_text) > 35:
                t_text = '{}..'.format(t_text[:33])
            self.write_centered_text(x1, x2, n_y, n_y + 23, t_text)
            cl.add_row(new_row, m_fun)
            n_y += 27

        for d_kb, d_fun in disp_list:
            self.canvas.bind(d_kb, d_fun)
            self._button_binds.append(d_kb)

        self.canvas.focus_force()
        self.root.bind('<FocusOut>', self.lost_focus)
        self.canvas.bind('<Escape>', self.lost_focus)

        self.canvas.bind('<Return>', cl.pick_selected)
        self.canvas.bind('<Up>', cl.selector(-1))
        self.canvas.bind('<Down>', cl.selector(+1))

        self._button_binds.extend(['<Escape>', '<Return>', '<Up>', '<Down>'])

    # -- fading -- #

    def _fade(self, _to, step):

        progress = self.root.attributes('-alpha')
        progress += step
        self.root.attributes('-alpha', progress)

        if (step < 0 and progress <= _to) or (step >= 0 and progress >= _to):
            return True

    def fade_out(self):
        step = -self.c.DEFAULT_OPACITY / self.c.FADE_N

        return self._fade(0, step)

    def fade_in(self):
        _to = self.c.DEFAULT_OPACITY
        step = _to / self.c.FADE_N

        return self._fade(_to, step)

    def wait_pls(self):

        def wait_fun():
            wait_fun.left -= 1
            return wait_fun.left <= 0

        wait_fun.left = self.c.CLEAR_TIMEOUT

        return wait_fun

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

    # -- draw queue -- #
    def enqueue_draw(self, job_type, job_funs):
        new_job = DrawJob(job_type, job_funs)

        was_empty = self._job_queue.empty()
        self._job_queue.put(new_job)

        if was_empty:
            # start the queue
            self.next_draw()
            return

        last_job = self._job_queue.queue[-2]
        last_job.cancel_remaining()

    def next_draw(self):
        if self._job_queue.empty():
            return

        cur_job = self._job_queue.queue[0]

        next_fun = cur_job.next_up()
        if next_fun is None:
            self._job_queue.get()
            self.next_draw()
        else:
            job_done = next_fun()
            if bool(job_done):
                cur_job.last_done()
                self.next_draw()
            else:
                self.root.after(self.c.FRAME_DUR, self.next_draw)

    def meat_wrapper(self, meat_fun):

        def wrapped():
            meat_fun()
            return True

        return wrapped

    def fo_draw(self):
        self.enqueue_draw('fade_out', [self.fade_out])

    def fofi_draw(self, job_type, meat_fun):
        # fade out -> (__) -> fade in
        all_funs = [self.fade_out, self.meat_wrapper(meat_fun),
                    self.fade_in]

        self.enqueue_draw(job_type, all_funs)

    def fofifo_draw(self, job_type, meat_fun):
        # fade out -> (__) -> fade in -> wait -> fade out
        all_funs = [self.fade_out, self.meat_wrapper(meat_fun),
                    self.fade_in, self.wait_pls(), self.fade_out]
        self.enqueue_draw(job_type, all_funs)


class DrawJob:
    def __init__(self, job_type, funs):
        """
        pre/post funs are for fading out/in
        meat_fun is the meat of the drawing job

        eventually draw jobs of the same type can have more complex behavior
        (recoloring things instead of clearing screen & redrawing))
        """
        self.job_type = job_type

        self._funs = funs
        self.last_fun_i = -1

    def next_up(self):
        funs = [(i, f) for i, f in enumerate(self._funs) if f is not None]
        if len(funs) == 0:
            return
        self.last_fun_i = funs[0][0]
        return funs[0][1]

    def last_done(self):
        if self.last_fun_i > -1:
            self._funs[self.last_fun_i] = None

    def cancel_remaining(self):
        for i in range(max(0, self.last_fun_i), len(self._funs)):
            self._funs[i] = None


class CanvasList:
    def __init__(self, config, canvas, cur_i):
        self.canvas = canvas
        self.c = config

        self.activate_funs = []
        self.rows = []
        self.cur_i = 0 if cur_i < 0 else cur_i

    def add_row(self, new_row, row_fun):
        self.rows.append(new_row)
        self.activate_funs.append(row_fun)

    def pick_selected(self, *args):
        if self.cur_i < 0:
            return
        self.activate_funs[self.cur_i]()

    def selector(self, d_i):
        diff = d_i

        def change_select(*args):
            if not len(self.rows):
                return
            self.cur_i = (self.cur_i + diff) % len(self.rows)
            # update drawing
            self.canvas.itemconfig('list_row', fill=self.c.BORDER_COLOR)
            self.canvas.itemconfig(self.rows[self.cur_i], fill=self.c.SELECTION_COLOR)

        return change_select
