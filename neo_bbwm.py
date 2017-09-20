import bbwm.drawing as bb_draw
import bbwm.core as bb_core
import bbwm.win_api as bb_api

import tkinter as tk
import keyboard

class BBWM:
    def __init__(self, root):
        # config
        self.c = bb_core.Config()

        # "backend"
        self.win_methods = bb_api.WinMethods()
        self.win_methods.msg_processor = self.process_msgs
        # TODO change for multimonitor setups..
        desktop = self.win_methods.monitors[0][1].get_ws_dims(self.c)
        self.workspace = bb_core.Workspace(desktop)

        self.move_dir_funs = {
            'l': self.workspace.go_left,
            'r': self.workspace.go_right,
            'u': self.workspace.go_up,
            'd': self.workspace.go_down,
        }

        self.swap_dir_funs = {
            'l': self.workspace.swap_left,
            'r': self.workspace.swap_right,
            'u': self.workspace.swap_up,
            'd': self.workspace.swap_down,
        }

        # gui

        self.gui = bb_draw.BBDraw(root, desktop, self.c)
        self.gui.resplit_fun = self.resplit

        # setup keybinds
        self.setup_hotkeys()

        # rdy to go
        self.win_methods.start_monitoring()

    # movement

    def move_and_focus(self, d):
        if d not in self.move_dir_funs:
            return
        self.move_dir_funs[d]()
        self.refocus()
        # gui
        self.draw_parts()

    def swap_and_focus(self, d):
        if d not in self.swap_dir_funs:
            return
        self.swap_dir_funs[d]()
        self.resize_wins()
        self.refocus()

    def refocus(self):
        cp = self.workspace.cur_part
        if cp is not None:
            if cp.window is not None:
                cp.window.focus(True)
            else:
                # move mouse to empty partition
                self.win_methods.set_mouse_pos(cp.dims)    

    # tiling

    def tile(self):
        win = self.win_methods.get_focused_window()
        if win is not None:
            self.workspace.tile(win)
            if self.c.PRETTY_WINS:
                win.undecorate()
            self.resize_wins()
            self.refocus()
            # gui
            self.draw_parts()

    def tile_dir(self, d, find_win=True):
        win = None
        if find_win:
            win = self.win_methods.get_focused_window()
            if win is None:
                return
        if d == 'v':
            self.workspace.split_v(new_win=win)
        else:
            self.workspace.split_h(new_win=win)
        self.resize_wins()
        self.refocus()
        # gui
        self.draw_parts()

    def untile(self):
        untiled_part = self.workspace.untile()
        if untiled_part is None:
            return
        self.resize_wins()
        self.refocus()
        win = untiled_part.window
        if win is not None:
            if self.c.PRETTY_WINS:
                win.redecorate()
            # delet the window
            del self.win_methods.hwnd_to_win[win.hwnd]
            if win.part is not None:
                win.part.window = None
        # gui
        self.draw_parts()

    # editing partitions

    def rotate(self):
        self.workspace.rotate()
        self.resize_wins()
        self.refocus()
        # gui
        self.draw_parts()

    def resplit(self, part, new_r):
        self.workspace.resplit(part, new_r)
        self.resize_wins()
        # gui
        self.draw_parts()

    def resize_wins(self):
        all_parts = self.workspace.find_leaf_parts()
        for p in all_parts:
            if p.window is not None:
                win_dim = p.dims.get_win_dims(self.c)
                p.window.set_dims(win_dim)

    def promote_to_ws(self):
        cp = self.workspace.cur_part
        if cp is not None:
            self.workspace.promote(cp)

    # gui

    def draw_parts(self):
        self.gui.clear_screen()
        all_parts = self.workspace.find_leaf_parts()
        cur_part = self.workspace.cur_part 
        for p in all_parts:
            self.gui.draw_border(p.dims.get_win_dims(self.c), cur_part == p)
        self.gui.fade_immediately()

    def draw_splits(self):
        self.gui.clear_screen()
        self.gui.rdy_to_split()
        all_parts_with_splits = self.workspace.find_all_splits()
        for p in all_parts_with_splits:
            self.gui.draw_split(p)

    # maint

    def setup_hotkeys(self):
        keyboard.add_hotkey('windows+z', self.tile)

        keyboard.add_hotkey('windows+a', self.tile_dir, args=['h'])
        keyboard.add_hotkey('windows+s', self.tile_dir, args=['v'])

        keyboard.add_hotkey('windows+d', self.rotate)
        keyboard.add_hotkey('windows+f', self.promote_to_ws)

        keyboard.add_hotkey('windows+q', self.tile_dir, args=['h', False])
        keyboard.add_hotkey('windows+w', self.tile_dir, args=['v', False])

        keyboard.add_hotkey('windows+x', self.untile)

        keyboard.add_hotkey('windows+left', self.move_and_focus, args=['l'], trigger_on_release=True)
        keyboard.add_hotkey('windows+right', self.move_and_focus, args=['r'], trigger_on_release=True)
        keyboard.add_hotkey('windows+up', self.move_and_focus, args=['u'], trigger_on_release=True)
        keyboard.add_hotkey('windows+down', self.move_and_focus, args=['d'], trigger_on_release=True)

        # unforunately doing win+shift+[dir] causes weird behavior
        # sometimes it swaps, sometimes it doesn't
        keyboard.add_hotkey('ctrl+alt+left', self.swap_and_focus, args=['l'], trigger_on_release=True)
        keyboard.add_hotkey('ctrl+alt+right', self.swap_and_focus, args=['r'], trigger_on_release=True)
        keyboard.add_hotkey('ctrl+alt+up', self.swap_and_focus, args=['u'], trigger_on_release=True)
        keyboard.add_hotkey('ctrl+alt+down', self.swap_and_focus, args=['d'], trigger_on_release=True)

        keyboard.add_hotkey('ctrl+alt+q', self.quit_helper)
        keyboard.add_hotkey('windows+c', self.draw_parts)
        keyboard.add_hotkey('ctrl+alt+r', print, args=[self.workspace])

    def process_msgs(self, msg):
        # print(msg)
        if msg[0] == 'focus_win':
            # will need to choose workspace associated with the monitor
            w = self.win_methods._get_or_add_win(msg[1], False)
            if w is not None and w.part is not None:
                self.workspace.cur_part = w.part
        elif msg[0] == 'close_win':
            w = self.win_methods._get_or_add_win(msg[1], False)
            if w is not None and w.part is not None:
                self.workspace.untile(w.part)

                win = w.part.window
                if win is not None:
                    if win.part is not None:
                        win.part.window = None

                del self.win_methods.hwnd_to_win[msg[1]]
                self.resize_wins()
                self.refocus()

    def quit_helper(self):
        if self.c.PRETTY_WINS:
            for _, w in self.win_methods.hwnd_to_win.items():
                w.redecorate()
        self.gui.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    bbwm = BBWM(root)
    # run it
    root.mainloop()