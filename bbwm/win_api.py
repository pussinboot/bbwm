import keyboard
import win32con, win32gui


class TestBinds:
    def __init__(self, ws, gui):
        self.workspace = ws
        self.gui = gui
        self.setup_binds()
        self.gui.canvas.focus_set()
        self.draw_all_parts()


    def draw_all_parts(self):
        self.gui.clear()
        # print('-'*20)

        all_parts = self.workspace.find_leaf_parts()
        for p in all_parts:
            cur = self.workspace.cur_part == p
            self.gui.draw_border(p.dims, cur)
            # print(p)

        self.gui.draw_cursor(self.workspace.cur_part.dims)

    def paint_neighbors(self, d):
        ns = self.workspace.find_neighbors(d)
        for n in ns:
            self.gui.draw_fill(n.dims)

    def move(self, fun_dir):
        fun_dir()
        self.draw_all_parts()

    def tile(self, d=None):
        if d == 'h':
            self.workspace.split_h()
        elif d == 'v':
            self.workspace.split_v()
        else:
            self.workspace.tile()
        self.draw_all_parts()

    def untile(self):
        self.workspace.untile()
        self.draw_all_parts()

    def setup_binds(self):
        # canvas doesnt receive keybinds until it is focused
        # so focus on mouse click
        self.gui.canvas.bind("<1>", lambda e: self.gui.canvas.focus_set())

        self.gui.canvas.bind('q', lambda e: self.gui.root.destroy())

        self.gui.canvas.bind('a', lambda e: self.tile())
        self.gui.canvas.bind('z', lambda e: self.tile('h'))
        self.gui.canvas.bind('x', lambda e: self.tile('v'))
        self.gui.canvas.bind('v', lambda e: self.untile())

        self.gui.canvas.bind('d', lambda e: self.paint_neighbors('h'))
        self.gui.canvas.bind('s', lambda e: self.paint_neighbors('v'))

        # a - tile window
        # z - untile window
        self.gui.canvas.bind('<Left>', lambda e: self.move(self.workspace.go_left))
        self.gui.canvas.bind('<Right>', lambda e: self.move(self.workspace.go_right))
        self.gui.canvas.bind('<Up>', lambda e: self.move(self.workspace.go_up))
        self.gui.canvas.bind('<Down>', lambda e: self.move(self.workspace.go_down))
