import keyboard
import win32con, win32gui, win32api

from ctypes import windll

import threading

import time


try:
    from core import Dims
except:
    from .core import Dims


class TestBinds:
    def __init__(self, ws, gui):
        self.workspace = ws
        self.gui = gui

        self.win_methods = WinMethods(self.process_msgs)
        self.win_methods.start_monitoring()

        self.setup_binds()
        self.gui.canvas.focus_set()
        self.draw_all_parts()

    def valid_moves(self, d, n):
        vs = self.workspace.find_valid_moves(d, n)
        if vs is not None:
            for v in vs:
                self.gui.draw_fill(v.dims)

    def draw_all_parts(self):
        self.gui.clear()
        # print('-'*20)

        all_parts = self.workspace.find_leaf_parts()

        for p in all_parts:
            cur = self.workspace.cur_part == p
            self.gui.draw_border(p.dims, cur)
            # print(p)

        self.gui.draw_cursor(self.workspace.cur_part.dims)

    def print_cur(self):
        print(self.workspace)

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
        self.gui.canvas.bind('<Shift-Left>', lambda e: self.valid_moves('h', -1))
        self.gui.canvas.bind('<Shift-Right>', lambda e: self.valid_moves('h', 1))
        self.gui.canvas.bind('<Shift-Up>', lambda e: self.valid_moves('v', -1))
        self.gui.canvas.bind('<Shift-Down>', lambda e: self.valid_moves('v', 1))

        # 
        self.gui.canvas.bind('p', lambda e: self.print_cur())

    def process_msgs(self, msg):
        print(msg)


class WinWin:
    def __init__(self, handle):
        self.hwnd = handle
        # i may need to register an event handler to keep track of if the window
        # - gets focused
        # - is closed
        # - ... ?

    @property
    def dims(self):
        try:
            l, t, r, b = win32gui.GetWindowRect(self.hwnd)
            return Dims(l, t, r - l, b - t)
        except:
            return Dims(-1, -1, -1, -1)

    def set_dims(self, new_dims):
        try:
            win32gui.MoveWindow(self.hwnd, *new_dims, False)
            return True
        except:
            return False

    @property
    def is_decorated(self):
        try:
            if win32gui.GetWindowLong(self.hwnd, win32con.GWL_STYLE) & win32con.WS_CAPTION:
                return True
            else:
                return False
        except:
            pass

    def undecorate(self):
        # undecorate window (only do this once)
        if self.is_decorated:
            style = win32gui.GetWindowLong(self.hwnd, win32con.GWL_STYLE)
            style -= win32con.WS_CAPTION
            win32gui.SetWindowLong(self.hwnd, win32con.GWL_STYLE, style)

    def redecorate(self):
        # make it how it was
        if not self.is_decorated:
            style = win32gui.GetWindowLong(self.hwnd, win32con.GWL_STYLE)
            style += win32con.WS_CAPTION
            win32gui.SetWindowLong(self.hwnd, win32con.GWL_STYLE, style)

    @property
    def is_visible(self):
        try:
            return win32gui.ShowWindow(self.hwnd, win32con.SW_SHOWNORMAL)
        except:
            pass

    def hide(self):
        if self.is_visible:
            win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)

    def unhide(self):
        if not self.is_visible:
            win32gui.ShowWindow(self.hwnd, win32con.SW_SHOWNORMAL)

    @property
    def is_focused(self):
        try:
            return self.hwnd == win32gui.GetForegroundWindow()
        except win32gui.error:
            pass

    def focus(self, also_center=False):
        try:
            win32gui.SetForegroundWindow(self.hwnd)
            if also_center:
                return self.center_on_me()
            return True
        except:
            pass

    def center_on_me(self):
        try:
            d = self.dims
            win32api.SetCursorPos((d[0] + d[2] // 2, d[1] + d[3] // 2))
            return True
        except:
            pass


class WinMethods:
    def __init__(self, msg_processor):
        self.monitors = []
        self.find_monitors()
        # need to add some dict to map win handles to win objects
        # so that our hook can actually .. affect things

        self.msg_processor = msg_processor

        self.msg_type_to_action = {
            win32con.HSHELL_WINDOWCREATED: 'new_win',
            win32con.HSHELL_WINDOWDESTROYED: 'close_win',
            32772: 'focus_win',
        }

    def find_monitors(self):
        self.monitors = [(handle, Dims(*rect)) for handle, _, rect in win32api.EnumDisplayMonitors()]

    def monitor_from_point(self, point):
        try:
            handle = win32api.MonitorFromPoint(point, win32con.MONITOR_DEFAULTTONEAREST)
        except:
            return -1
        for i, m in enumerate(self.monitors):
            if handle == m[0]:
                return i
        return -1

    def get_all_windows(self):
        def callback(handle, tor):
            tor.append(WinWin(handle))
            return True

        windows = []
        win32gui.EnumWindows(callback, windows)

        return windows

    def get_focused_window(self):
        try:
            return WinWin(win32gui.GetForegroundWindow())
        except win32gui.error:
            pass

    def get_mouse_window(self):
        # returns window under mouse
        try:
            return WinWin(win32gui.WindowFromPoint(win32api.GetCursorPos()))
        except win32gui.error:
            pass
        except win32api.error:
            pass

    def _intercept_msgs(self):
        spy = WinTaskIcon()
        msg = spy.get_msg()
        while msg:
            # print(msg)
            # process msg
            lparam = msg[1][2]
            if lparam in self.msg_type_to_action:
                hwnd, point = msg[1][3], msg[1][5]
                monitor_i = self.monitor_from_point(point)

                self.msg_processor((self.msg_type_to_action[lparam], hwnd, monitor_i))

            msg = spy.get_msg()

    def start_monitoring(self):
        self.msg_thread = threading.Thread(target=self._intercept_msgs, daemon=True)
        self.msg_thread.start()

    def check_for_msgs(self):
        if not self.msg_queue.empty():
            return self.msg_queue.get()


class WinTaskIcon:
    # inspo: https://github.com/tzbob/python-windows-tiler/blob/master/pwt/notifyicon.py
    def __init__(self):
        window_class_name = "bbwm icon"
        # Register the Window class.
        window_class = win32gui.WNDCLASS()
        window_class.hInstance = win32gui.GetModuleHandle(None)
        window_class.lpszClassName = window_class_name
        window_class.style = win32con.CS_VREDRAW | win32con.CS_HREDRAW
        window_class.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        window_class.hbrBackground = win32con.COLOR_WINDOW
        reg_win_class = win32gui.RegisterClass(window_class)

        # create window
        self.hwnd = win32gui.CreateWindow(reg_win_class, window_class_name,
                                          win32con.WS_OVERLAPPED | win32con.WS_SYSMENU,  # style
                                          0, 0, win32con.CW_USEDEFAULT, win32con.CW_USEDEFAULT, 0, 0,
                                          window_class.hInstance, None)

        win32gui.UpdateWindow(self.hwnd)

        # draw icon
        # hold onto this in order to show balloons
        self.icon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)

        notify_id = (self.hwnd, 0,
                     win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP,
                     win32con.WM_USER + 20, self.icon,
                     "bbwm")  # hovertext

        win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, notify_id)
        self.register_shellhook()


    def destroy(self):
        self.unregister_shellhook()
        win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, (self.hwnd, 0))

    def register_shellhook(self):
        if windll.user32.RegisterShellHookWindow(self.hwnd):
            return True
        return False

    def unregister_shellhook(self):
        windll.user32.DeregisterShellHookWindow(self.hwnd)

    def get_msg(self):
        # this is blocking!!
        try:
            return win32gui.GetMessage(self.hwnd, 0, 0)
        except Exception as e:
            print(e)



if __name__ == '__main__':
    wm = WinMethods()
    # print(wm.monitors[0][1])
    st = wm.get_focused_window()
    a = wm.get_mouse_window()
    # move_meme = Dims(100, 100, 100, 100)
    # a.set_dims(move_meme)

    # a.hide()
    # time.sleep(1)
    # a.unhide()

    print(a.is_focused)
    a.focus(True)
    time.sleep(0.1)
    print(a.is_focused)



