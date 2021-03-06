import bbwm.drawing as bb_draw
import bbwm.core as bb_core
import bbwm.win_api as bb_api

import bbwm.tiling as bb_tile

import tkinter as tk


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
        self._hiding_wins = 0
        self._just_closed = False

        self.workspaces = []
        disp_dims = []
        for _, display_dims in self.win_methods.monitors:
            disp_dims.append(display_dims)
            desktop = display_dims.get_ws_dims(self.c)
            self.workspaces.append([bb_core.Workspace(desktop) for _ in range(self.c.NO_WORKSPACES)])

        self.display_nav = bb_core.calc_display_nav(disp_dims)

        self.cur_adjust_part = None
        self.cur_adjust_stack = []

        # gui
        self.gui = bb_draw.BBDraw(root, self.win_methods.monitor_bbox, self.c)
        self.gui.resplit_fun = self.resplit
        self.gui.unfocus_fun = self.refocus
        self.win_methods.set_topmost(root.winfo_id())

        self.hotkey_to_fun = {}
        self.setup_hotkeys()

        # temp binds for popup menus

        # monitor changing
        def m_kb(dir):
            d = dir

            def m_kb_fun(*args):
                self.change_display(d, False)
                self.draw_workspaces()

            return m_kb_fun

        self.display_changers = [('<Home>', m_kb('u')),
                                 ('<End>', m_kb('d')),
                                 ('<Delete>', m_kb('l')),
                                 ('<Next>', m_kb('r'))]  # page down

        # split adjustment
        def gen_split_adjust_fun(adj):
            d = adj

            def adjuster(*args):
                cur_ratio = int(self.cur_adjust_part.split.r * self.c.N_KB_RATIOS)
                new_ratio = cur_ratio + d
                new_ratio = max(1, min(self.c.N_KB_RATIOS - 1, new_ratio))
                self.resplit(self.cur_adjust_part, new_ratio / self.c.N_KB_RATIOS, False)
                self.gui.move_split(self.cur_adjust_part)

            return adjuster

        def split_adjust_picker_fun(h_key, v_key):
            key_lu = [h_key, v_key]

            def picked_adjust_fun(*args):
                if self.cur_adjust_part is None:
                    return
                key = key_lu[self.cur_adjust_part.split.d == 'v']
                self.split_adjusters[key]()

            return picked_adjust_fun

        self.split_adjusters = {
            '-': gen_split_adjust_fun(-1),
            '+': gen_split_adjust_fun(+1),
            'up': self._split_adjust_go_up,
            'down': self._split_adjust_go_down,
        }

        self.split_adjust_binds = [
            ('<Left>', split_adjust_picker_fun('-', 'up')),
            ('<Right>', split_adjust_picker_fun('+', 'down')),
            ('<Up>', split_adjust_picker_fun('up', '-')),
            ('<Down>', split_adjust_picker_fun('down', '+')),
            ('<Tab>', self._split_adjust_go_next)
        ]

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
            all_parts = self.workspace.find_leaf_parts()
            self._hiding_wins = len(all_parts)
            for p in all_parts:
                if p.window is not None:
                    p.window.hide()
                else:
                    self._hiding_wins -= 1

        # show new one
        self.workspace_inds[self.display_ind] = new_ind
        all_parts = self.workspace.find_leaf_parts()
        for p in all_parts:
            if p.window is not None:
                p.window.unhide()
        # restore focus
        if self.workspace.cur_part.window is not None:
            self.workspace.cur_part.window.focus(True)

        self.draw_parts()

    def change_display(self, dx, redraw=True):
        nav_dirs = self.display_nav[self.display_ind]
        next_disp = nav_dirs.get(dx)
        if next_disp is None:
            return
        self.display_ind = next_disp

        cp = self.workspace.cur_part
        if redraw and cp.window is not None:
            cp.window.focus(True)
        else:
            self.win_methods.set_mouse_pos(cp.dims)

        if redraw:
            self.draw_parts()

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
            self.draw_parts()

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

    def tile_dir(self, d):
        new_win = self.win_methods.get_focused_window()

        if new_win is not None:
            new_win = None if new_win.part is not None else new_win

        if new_win is not None and self.c.PRETTY_WINS:
            new_win.undecorate()

        self.workspace._split(d, new_win=new_win)

        self.resize_wins()
        self.refocus()

    def untile(self):
        untiled_part = self.workspace.untile()
        if untiled_part is None:
            return

        win = untiled_part.window
        if win is not None:
            if self.c.PRETTY_WINS:
                win.redecorate()
            # delet the window
            if win.hwnd in self.win_methods.hwnd_to_win:
                del self.win_methods.hwnd_to_win[win.hwnd]
            if win.part is not None:
                win.part.window = None

        self.resize_wins()
        self.refocus()

    # editing partitions

    def rotate(self):
        self.workspace.rotate()
        self.resize_wins()
        self.refocus()

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

        return picker_fun

    def _draw_workspaces(self):
        self.gui.clear_screen()
        win_list = []
        x, y = self.gui._calc_mon_offset()
        cur_i = -1

        disp_hints = {
            'u': 'Home',
            'd': 'End',
            'l': 'Del',
            'r': 'Pg ⇩'
        }

        nav_dirs = self.display_nav[self.display_ind]
        nav_hints = ['' for _ in range(len(nav_dirs))]
        for nd, disp_i in nav_dirs.items():
            if disp_i is not None:
                nav_hints[disp_i] = disp_hints[nd]

        for i, (_, display_dims) in enumerate(self.win_methods.monitors):
            self.gui.draw_monitor(display_dims, x, y, nav_hints[i])
            if i == self.display_ind:
                all_parts = self.workspace.find_leaf_parts()
                cur_part = self.workspace.cur_part
                c = 1
                for p in all_parts:
                    if p.window is not None:
                        txt = c
                        win_list.append((c, p.window.title, self._part_picker(p)))
                        if p == cur_part:
                            cur_i = c - 1
                        c += 1
                    else:
                        txt = ''
                    self.gui.draw_win(p.dims.get_win_dims(self.c), x, y, txt, p == cur_part)

        self.gui.draw_menu_list(win_list, self.display_changers, x, y, cur_i)

    def draw_workspaces(self):
        self.gui.fofi_draw('workspaces', self._draw_workspaces)

    def draw_parts(self):
        all_parts = self.workspace.find_leaf_parts()
        cur_part = self.workspace.cur_part

        def draw_later():
            self.gui.clear_screen()
            for p in all_parts:
                self.gui.draw_part(p.dims.get_win_dims(self.c), cur_part == p)

        self.gui.fofifo_draw('parts', draw_later)

    def _redraw_splits(self):
        self.gui.clear_screen()
        for s_s in self.cur_adjust_part.split_siblings:
            if s_s == self.cur_adjust_part:
                continue
            self.gui.draw_part(s_s.dims, False)
            self.gui.draw_split(s_s, False, False)

        self.gui.draw_part(self.cur_adjust_part.dims, True, True)
        self.gui.draw_split(self.cur_adjust_part, True)

    def draw_splits(self):
        self.cur_adjust_part = self.workspace.cur_part.parent
        if self.cur_adjust_part is None:
            return

        self.cur_adjust_stack = []

        self.gui.split_menu(self.split_adjust_binds)
        self.gui.fofi_draw('splits', self._redraw_splits)

    def _split_adjust_go_up(self, *args):
        if self.cur_adjust_part.parent is None:
            return
        self.cur_adjust_stack.append(self.cur_adjust_part)
        self.cur_adjust_part = self.cur_adjust_part.parent
        self._redraw_splits()

    def _split_adjust_go_down(self, *args):
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

    def _split_adjust_go_next(self, *args):
        poss_next = self.cur_adjust_part.split_siblings
        lpn = len(poss_next)
        if lpn <= 1:
            return
        cur_i = poss_next.index(self.cur_adjust_part)
        self.cur_adjust_part = poss_next[(cur_i + 1) % lpn]
        self.cur_adjust_stack = []
        self._redraw_splits()

    def draw_menu(self):

        tags_to_funs = [
            ('dflt', self.to_default_scheme),
            ('mono', lambda: print('not implemented yet')),
            ('horz', self.to_horiz_scheme),
            ('vert', lambda: print('not implemented yet')),
        ]

        def draw_later():
            self.gui.clear_screen()
            self.gui.draw_menu(tags_to_funs)

        self.gui.fofi_draw('menu', draw_later)

    # maint

    def _add_hotkey(self, key_combo, func, args=[], trigger_on_release=False, suppress=True):
        new_hk_id = self.win_methods.add_hotkey(key_combo)
        rrr = args

        def execute():
            func(*rrr)

        self.hotkey_to_fun[new_hk_id] = execute

    def setup_hotkeys(self):
        all_binds = [
            # fake
            ('alt+f5', self.tile),
            ('alt+f6', self.untile, [], True),
            ('alt+f7', self.rotate, [], True),

            ('alt+f8', self.tile_dir, ['h']),
            ('alt+f9', self.tile_dir, ['v']),
            ('ctrl+f6', self.tile_dir, ['n']),

            ('alt+f10', self.draw_splits),
            ('alt+f11', self.draw_menu),
            ('alt+f12', self.draw_workspaces),

            ('win+f5', self.move_and_focus, ['u'], True),
            ('win+f6', self.move_and_focus, ['d'], True),
            ('win+f7', self.move_and_focus, ['l'], True),
            ('win+f8', self.move_and_focus, ['r'], True),

            ('win+f9', self.swap_and_focus, ['u'], True),
            ('win+f10', self.swap_and_focus, ['d'], True),
            ('win+f11', self.swap_and_focus, ['l'], True),
            ('win+f12', self.swap_and_focus, ['r'], True),

            ('win+f2', self.change_workspace, [0], True),
            ('win+f3', self.change_workspace, [1], True),
            ('win+f4', self.change_workspace, [2], True),

            ('ctrl+alt+home', self.change_display, ['u'], True),
            # real
            ('win+end', self.change_display, ['d'], True),
            ('win+delete', self.change_display, ['l'], True),
            ('win+pgdown', self.change_display, ['r'], True),

            ('win+shift+q', self.quit_helper),
            ('win+shift+r', self.debug_display),
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
            if self._hiding_wins > 0:
                self._hiding_wins -= 1
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
        elif msg[0] in self.hotkey_to_fun:
            self.hotkey_to_fun[msg[0]]()

    def quit_helper(self):
        for _, w in self.win_methods.hwnd_to_win.items():
            try:
                if w.part is not None:
                    w.unhide()
                    if self.c.PRETTY_WINS:
                        w.redecorate()
            except:
                pass

        if self.win_methods.spy is not None:
            self.win_methods.unbind_hotkeys()
            self.win_methods.spy.destroy()
        self.gui.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    bbwm = BBWM(root)
    # run it
    root.mainloop()
