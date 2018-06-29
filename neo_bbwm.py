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
        self._just_closed = False

        self.workspaces = []
        for _, display_dims in self.win_methods.monitors:
            desktop = display_dims.get_ws_dims(self.c)
            self.workspaces.append([bb_core.Workspace(desktop) for _ in range(self.c.NO_WORKSPACES)])

        self.cur_adjust_part = None
        self.cur_adjust_stack = []

        # gui
        self.gui = bb_draw.BBDraw(root, self.win_methods.monitor_bbox, self.c)
        self.gui.resplit_fun = self.resplit
        self.gui.unfocus_fun = self.refocus
        # self.win_methods.hwnd_to_win[self.gui.hwnd] = None

        # setup keybinds
        self.setup_hotkeys()
        # temp binds for popup menus

        def m_kb(dir):
            d = dir

            def m_kb_fun(*args):
                self.change_display(d)
                self.draw_workspaces()

            return m_kb_fun

        self.display_changers = [('<Prior>', m_kb(+1)), ('<Next>', m_kb(-1))]

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
            # move mouse to (empty) partition
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
        if keyboard.is_pressed('shift'):
            return
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

    def resplit(self, part, new_r, redraw=True):
        self.workspace.resplit(part, new_r)
        self.resize_wins()
        # gui
        if redraw:
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
        d_i = self.display_ind
        l_m = len(self.win_methods.monitors)
        monitor_hints = {((d_i - 1) % l_m): 'Pg ⇩', ((d_i + 1) % l_m): 'Pg ⇧'}

        for i, (_, display_dims) in enumerate(self.win_methods.monitors):
            self.gui.draw_monitor(display_dims, x, y, monitor_hints.get(i, ''))
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

        self.gui.draw_menu_list(win_list, self.display_changers, x, y)
        self.gui.fade_in()

    def draw_parts(self):
        self.gui.clear_screen()
        all_parts = self.workspace.find_leaf_parts()
        cur_part = self.workspace.cur_part
        for p in all_parts:
            self.gui.draw_part(p.dims.get_win_dims(self.c), cur_part == p)
        self.gui.fade_immediately()

    def _redraw_splits(self):
        self.gui.draw_part(self.cur_adjust_part.dims, True, True)
        self.gui.draw_split(self.cur_adjust_part, True)

    def draw_splits(self):
        self.gui.clear_screen()
        self.cur_adjust_part = self.workspace.cur_part.parent
        if self.cur_adjust_part is None:
            return

        self.cur_adjust_stack = []
        self.gui.rdy_to_split()
        self._redraw_splits()

        def gen_adjust_fun(adj):
            d = adj

            def adjuster(*args):
                cur_ratio = int(self.cur_adjust_part.split.r * self.c.N_KB_RATIOS)
                new_ratio = cur_ratio + d
                new_ratio = max(1, min(self.c.N_KB_RATIOS - 1, new_ratio))
                self.resplit(self.cur_adjust_part, new_ratio / self.c.N_KB_RATIOS, False)
                self.gui.move_split(self.cur_adjust_part)

            return adjuster

        def go_up(*args):
            if self.cur_adjust_part.parent is None:
                return
            self.cur_adjust_stack.append(self.cur_adjust_part)
            self.cur_adjust_part = self.cur_adjust_part.parent
            self._redraw_splits()

        def go_down(*args):
            if self.cur_adjust_part.is_empty:
                return
            elif len(self.cur_adjust_stack) != 0:
                self.cur_adjust_part = self.cur_adjust_stack.pop()
                self._redraw_splits()
            else:
                poss_next = [c for c in self.cur_adjust_part.children if c.split is not None]
                if len(poss_next) == 0:
                    return
                self.cur_adjust_part = poss_next[0]
                self._redraw_splits()

        def go_next(*args):
            poss_next = [c for c in self.cur_adjust_part.siblings if c.split is not None]
            lpn = len(poss_next)
            if lpn <= 1:
                return
            cur_i = poss_next.index(self.cur_adjust_part)
            self.cur_adjust_part = poss_next[(cur_i + 1) % lpn]
            self.cur_adjust_stack = []
            self._redraw_splits()

        temp_binds = [
            ('<Left>', gen_adjust_fun(-1)), ('<Right>', gen_adjust_fun(1)),
            ('<Up>', go_up), ('<Down>', go_down), ('<Tab>', go_next)
        ]

        self.gui.split_menu(temp_binds)

        # all_parts_with_splits = self.workspace.find_all_splits()
        # for p in all_parts_with_splits:
        #     self.gui.draw_split(p)

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

    def _add_hotkey(self, hotkey, func, args=[], trigger_on_release=False, suppress=True):
        keyboard.add_hotkey(hotkey, func, args=args, suppress=suppress,
                            trigger_on_release=trigger_on_release)

    def setup_hotkeys(self):
        all_binds = [
            ('windows+z', self.tile),
            ('windows+d', self.rotate),
            ('windows+x', self.untile),

            ('windows+a', self.tile_dir, ['h']),
            ('windows+s', self.tile_dir, ['v']),

            ('windows+f', self.draw_splits),
            ('windows+q', self.draw_menu),
            ('windows+w', self.draw_workspaces),

            ('windows+left', self.move_and_focus, ['l'], True),
            ('windows+right', self.move_and_focus, ['r'], True),
            ('windows+up', self.move_and_focus, ['u'], True, False),
            ('windows+down', self.move_and_focus, ['d'], True, False),

            # unforunately doing win+shift+[dir] causes weird behavior
            # sometimes it swaps, sometimes it doesn't
            ('ctrl+alt+left', self.swap_and_focus, ['l'], True),
            ('ctrl+alt+right', self.swap_and_focus, ['r'], True),
            ('ctrl+alt+up', self.swap_and_focus, ['u'], True),
            ('ctrl+alt+down', self.swap_and_focus, ['d'], True),

            ('ctrl+alt+1', self.change_workspace, [0], True),
            ('ctrl+alt+2', self.change_workspace, [1], True),
            ('ctrl+alt+3', self.change_workspace, [2], True),

            ('windows+page up', self.change_display, [+1], True),
            ('windows+page down', self.change_display, [-1], True),

            ('ctrl+alt+q', self.quit_helper),
            ('ctrl+alt+r', self.debug_display),
        ]

        for bind in all_binds:
            self._add_hotkey(*bind)

    def process_msgs(self, msg):
        if msg[0] == 'focus_win':
            w = self.win_methods._get_or_add_win(msg[1], False)
            if w is not None and w.part is not None:
                self.display_ind = msg[2]
                self.workspace.cur_part = w.part
                if self._just_closed:
                    self.refocus()

            self._just_closed = False
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
                self._just_closed = True

    def quit_helper(self):
        if self.c.PRETTY_WINS:
            for _, w in self.win_methods.hwnd_to_win.items():
                try:
                    w.redecorate()
                except:
                    pass
        if self.win_methods.spy is not None:
            self.win_methods.spy.destroy()
        self.gui.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    bbwm = BBWM(root)
    # run it
    root.mainloop()
