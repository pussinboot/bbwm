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

        self.width, self.height = base_dims.w, base_dims.h
        w, h = self.width + 2 * c.OFF_SCREEN, self.height + 2 * c.OFF_SCREEN
        x, y = -c.OFF_SCREEN, -c.OFF_SCREEN
        self.root.geometry('%dx%d+%d+%d' % (w, h, x, y))

        self.canvas = tk.Canvas(root, width=w, height=h, bg="#0DEAD0")
        self.canvas.pack()

    def draw_border(self, dims, current):
        outline = self.c.BORDER_HIGHLIGHT_COLOR if current else self.c.BORDER_COLOR

        x, y, w, h = dims.x, dims.y, dims.w, dims.h
        x, y = x + self.c.OFF_SCREEN, y + self.c.OFF_SCREEN
        rx = x + w
        by = y + h

        w = max(min(self.c.INNER_SPACING_X, self.c.INNER_SPACING_Y) - 2, 2)

        self.canvas.create_rectangle(x, y, rx, by, outline=outline, width=w)

    def clear_screen(self):
        self.canvas.delete('all')
