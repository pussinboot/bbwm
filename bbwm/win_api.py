import keyboard
import win32con, win32gui


class TestBinds:
    def __init__(self, ws, gui):
        self.workspace = ws
        self.gui = gui

        self.setup_binds()

    def draw_all_parts(self):
        all_parts = self.workspace.traverse()
        for p in all_parts:
            cur = self.workspace.cur_part == p
            self.gui.draw_border(p.dims, cur)

    def setup_binds(self):
        # canvas doesnt receive keybinds until it is focused
        # so focus on mouse click
        self.gui.canvas.bind("<1>", lambda e: self.gui.canvas.focus_set())

        self.gui.canvas.bind('d', lambda e: self.draw_all_parts())
        # a - tile window
        # z - untile window