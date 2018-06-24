import bbwm.drawing as bb_draw
import bbwm.core as bb_core
import bbwm.win_api as bb_api

import bbwm.tiling as bb_tile

import tkinter as tk
import keyboard


class BBWM:
    def __init__(self, root):
        # config
        self.c = bb_core.Config()

        # "backend"
        self.win_methods = bb_api.WinMethods()
        self.win_methods.msg_processor = self.process_msgs

        self.num_displays = len(self.win_methods.monitors)

        self.display_ind = 0
        self.workspace_inds = [0] * self.num_displays
        self._hiding_wins = False

        self.workspaces = []
        for _, display_dims in self.win_methods.monitors:
            desktop = display_dims.get_ws_dims(self.c)
            self.workspaces.append([bb_core.Workspace(desktop) for _ in range(self.c.NO_WORKSPACES)])

        # gui
        self.gui = bb_draw.BBDraw(root, self.win_methods.monitor_bbox, self.c)
        self.gui.resplit_fun = self.resplit

        # setup keybinds
        self.setup_hotkeys()

        # rdy to go
        self.win_methods.start_monitoring()

    # workspaces

    @property
    def workspace(self):
        d_i = self.display_ind
        return self.workspaces[d_i][self.workspace_inds[d_i]]

    def change_workspace(self, new_ind):
        if new_ind >= self.c.NO_WORKSPACES:
            return
        # hide cur workspace
        if new_ind != self.workspace_inds[self.display_ind]:
            self._hiding_wins = True
            all_parts = self.workspace.find_leaf_parts()
            for p in all_parts:
                if p.window is not None:
                    p.window.hide()

        self._hiding_wins = False

        # show new one
        self.workspace_inds[self.display_ind] = new_ind
        all_parts = self.workspace.find_leaf_parts()
        for p in all_parts:
            if p.window is not None:
                p.window.unhide()
                p.window.focus()  # do this to bring them all up front again
        # restore focus
        if self.workspace.cur_part.window is not None:
            self.workspace.cur_part.window.focus(True)

    def change_display(self, d):

        self.display_ind = (self.display_ind + d) % self.num_displays

        cp = self.workspace.cur_part
        if cp.window is not None:
            cp.window.focus(True)
        else:
            self.win_methods.set_mouse_pos(cp.dims)

    def debug_display(self):
        print(self.workspace)
        print(self.display_ind, self.workspace_inds)

    # movement

    def move_and_focus(self, d):
        move_dir_funs = {
            'l': self.workspace.go_left,
            'r': self.workspace.go_right,
            'u': self.workspace.go_up,
            'd': self.workspace.go_down,
        }

        if d not in move_dir_funs:
            return

        move_dir_funs[d]()
        self.refocus()
        # gui
        self.draw_parts()

    def swap_and_focus(self, d):
        swap_dir_funs = {
            'l': self.workspace.swap_left,
            'r': self.workspace.swap_right,
            'u': self.workspace.swap_up,
            'd': self.workspace.swap_down,
        }

        if d not in swap_dir_funs:
            return

        swap_dir_funs[d]()
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
        if win is not None and win.part is None:
            if not self.workspace.tile(win):
                return

            if self.c.PRETTY_WINS:
                win.undecorate()
            self.resize_wins()
            self.refocus()
            # gui
            self.draw_parts()

    def tile_dir(self, d):
        new_win = self.win_methods.get_focused_window()
        new_win = None if new_win.part is not None else new_win

        if new_win is not None and self.c.PRETTY_WINS:
            new_win.undecorate()

        if d == 'v':
            self.workspace.split_v(new_win=new_win)
        else:
            self.workspace.split_h(new_win=new_win)

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
            if win.hwnd in self.win_methods.hwnd_to_win:
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

    def change_scheme(self, new_ts):
        cp = self.workspace.cur_part
        if cp.parent is not None:
            cp = cp.parent
        cp.assoc_ts = new_ts
        aff_parts = self.workspace._traverse(cp)

        # grr, this doesn't work..
        # i want it to resplit everything

        # orphans = [p for p in cp.children]
        # cp.children = []

        # for p in orphans:
        #     p_win = p.window
        #     if p_win is not None:
        #         p_win.part = None
        #     new_ts.tile(p, p_win)

        for p in aff_parts:
            p.assoc_ts = new_ts
            p.resize_from_parent()

        self.resize_wins()
        # gui
        self.draw_parts()  # needs delay or proper cancel from menu fadeout

    def to_default_scheme(self):
        d_ts = bb_tile.DefaultTilingScheme()
        self.change_scheme(d_ts)

    def to_horiz_scheme(self):
        h_ts = bb_tile.HorizontalTilingScheme()
        self.change_scheme(h_ts)

    # gui
    def _part_picker(self, part):
        p = part

        def picker_fun(*args):
            self.workspace.cur_part = p
            self.refocus()
            self.gui.fade_immediately()

        return picker_fun

    def draw_workspaces(self):
        self.gui.clear_screen()
        win_list = []
        x, y = self.gui.calc_mon_offset()
        for i, (_, display_dims) in enumerate(self.win_methods.monitors):
            self.gui.draw_monitor(display_dims, x, y)
            if i == self.display_ind:
                all_parts = self.workspace.find_leaf_parts()
                cur_part = self.workspace.cur_part
                c = 1
                for p in all_parts:
                    if p.window is not None:
                        txt = c
                        win_list.append((c, p.window.title, self._part_picker(p)))
                        c += 1
                    else:
                        txt = ''
                    self.gui.draw_win(p.dims.get_win_dims(self.c), x, y, txt, p == cur_part)
        self.gui.draw_menu_list(win_list, x, y)
        self.gui.fade_in()

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

    def draw_menu(self):
        self.gui.clear_screen()

        tags_to_funs = [
            ('dflt', self.to_default_scheme),
            ('mono', lambda: print('not implemented yet')),
            ('horz', self.to_horiz_scheme),
            ('vert', lambda: print('not implemented yet')),
        ]

        self.gui.draw_menu(tags_to_funs)
        self.gui.fade_in()

    # maint

    def setup_hotkeys(self):
        keyboard.add_hotkey('windows+z', self.tile)
        keyboard.add_hotkey('windows+d', self.rotate)
        keyboard.add_hotkey('windows+x', self.untile)

        keyboard.add_hotkey('windows+a', self.tile_dir, args=['h'])
        keyboard.add_hotkey('windows+s', self.tile_dir, args=['v'])

        keyboard.add_hotkey('windows+f', self.draw_splits)
        keyboard.add_hotkey('windows+q', self.draw_menu)
        keyboard.add_hotkey('windows+w', self.draw_workspaces)

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

        keyboard.add_hotkey('ctrl+alt+1', self.change_workspace, args=[0], trigger_on_release=True)
        keyboard.add_hotkey('ctrl+alt+2', self.change_workspace, args=[1], trigger_on_release=True)
        keyboard.add_hotkey('ctrl+alt+3', self.change_workspace, args=[2], trigger_on_release=True)

        keyboard.add_hotkey('windows+page up', self.change_display, args=[+1], trigger_on_release=True)
        keyboard.add_hotkey('windows+page down', self.change_display, args=[-1], trigger_on_release=True)

        keyboard.add_hotkey('ctrl+alt+q', self.quit_helper)
        keyboard.add_hotkey('ctrl+alt+r', self.debug_display)

    def process_msgs(self, msg):
        if msg[0] == 'focus_win':
            # will need to choose workspace associated with the monitor
            w = self.win_methods._get_or_add_win(msg[1], False)
            if w is not None and w.part is not None:
                self.display_ind = msg[2]
                self.workspace.cur_part = w.part
        elif msg[0] == 'close_win':
            # apparently hiding windows sends the same msg as closing them..
            if self._hiding_wins:
                return
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
        if self.win_methods.spy is not None:
            self.win_methods.spy.destroy()
        self.gui.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    bbwm = BBWM(root)
    # run it
    root.mainloop()
