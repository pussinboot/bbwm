import win32con, win32gui, win32api
import win32com.client
from ctypes import windll

import threading

import time


try:
    from core import Dims, Workspace
except:
    from .core import Dims, Workspace


class WinWin:
    def __init__(self, handle, shell):
        self.hwnd = handle
        self.part = None
        self.shell = shell

    @property
    def dims(self):
        try:
            l, t, r, b = win32gui.GetWindowRect(self.hwnd)
            return Dims(l, t, r - l, b - t)
        except:
            return Dims(-1, -1, -1, -1)

    def set_dims(self, new_dims):
        try:
            # show it if it is hidden..
            win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
            win32gui.MoveWindow(self.hwnd, *new_dims, True)
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
            # need to do stupid thing..
            # see remarks from here: https://msdn.microsoft.com/en-us/library/windows/desktop/ms633539(v=vs.85).aspx
            self.shell.SendKeys('+')
            win32gui.SetForegroundWindow(self.hwnd)
            win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)            
            if also_center:
                return self.center_on_me()
            return True
        except Exception as e:
            print(e)

    def center_on_me(self):
        try:
            d = self.dims
            win32api.SetCursorPos((d.midpoint()))
            return True
        except:
            pass


class WinMethods:
    def __init__(self, msg_processor=None):
        self.monitors = []
        self.find_monitors()

        self.hwnd_to_win = {}

        if msg_processor is None:
            msg_processor = lambda m: None

        self.msg_processor = msg_processor

        self.msg_type_to_action = {
            win32con.HSHELL_WINDOWCREATED: 'new_win',
            win32con.HSHELL_WINDOWDESTROYED: 'close_win',
            32772: 'focus_win',
        }

        self.shell = win32com.client.Dispatch("WScript.Shell")

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
            tor.append(WinWin(handle, self.shell))
            return True

        windows = []
        win32gui.EnumWindows(callback, windows)

        return windows

    def _get_or_add_win(self, hwnd, add_it=True):
        if hwnd not in self.hwnd_to_win:
            if add_it:
                self.hwnd_to_win[hwnd] = WinWin(hwnd, self.shell)
            else:
                return
        return self.hwnd_to_win[hwnd]

    def get_focused_window(self, only_existing=False):
        try:
            hwnd = win32gui.GetForegroundWindow()
            return self._get_or_add_win(hwnd, not only_existing)
        except win32gui.error:
            pass

    def get_mouse_window(self, only_existing=False):
        # returns window under mouse
        try:
            hwnd = win32gui.WindowFromPoint(win32api.GetCursorPos())
            return self._get_or_add_win(hwnd, not only_existing)
        except win32gui.error:
            pass
        except win32api.error:
            pass

    def set_mouse_pos(self, dims):
        win32api.SetCursorPos((dims.midpoint()))

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

                self._handle_msg((self.msg_type_to_action[lparam], hwnd, monitor_i))

            msg = spy.get_msg()

    def _handle_msg(self, msg):
        msg_type, hwnd = msg[0], msg[1]
        if msg_type == 'new_win':
            if hwnd not in self.hwnd_to_win:
                self.hwnd_to_win[hwnd] = WinWin(hwnd, self.shell)
            else:
                return
        elif msg_type == 'close_win':
            if hwnd not in self.hwnd_to_win:
                return
        elif msg_type == 'focus_win':
            if hwnd not in self.hwnd_to_win:
                return
        self.msg_processor(msg)

    def start_monitoring(self):
        self.msg_thread = threading.Thread(target=self._intercept_msgs, daemon=True)
        self.msg_thread.start()


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

