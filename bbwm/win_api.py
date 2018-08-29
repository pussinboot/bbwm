import threading
import win32con
import win32gui
import win32api

import win32com.client
from ctypes import windll

from .core import Dims

from collections import namedtuple


# regex for custom stuff
BANNED_WINDOW_TITLES = ['__bbwm__', 'Cortana', 'Blackbox']


class WinWin:
    def __init__(self, handle, shell):
        self.hwnd = handle
        self.part = None
        self.shell = shell

    def __str__(self):
        str_repr = 'win: {}'.format(self.hwnd)
        if self.part is not None:
            str_repr = '{}\tpart: {}'.format(str_repr, self.part)
        return str_repr

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
            try:
                win32gui.SetWindowLong(self.hwnd, win32con.GWL_STYLE, style)
                win32gui.SetWindowPos(self.hwnd, 0, 0, 0, 0, 0,
                                      win32con.SWP_FRAMECHANGED +
                                      win32con.SWP_NOMOVE +
                                      win32con.SWP_NOSIZE +
                                      win32con.SWP_NOZORDER)
            except:
                pass

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
            win32gui.BringWindowToTop(self.hwnd)

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
        except:
            pass

    def center_on_me(self):
        try:
            d = self.dims
            win32api.SetCursorPos((d.midpoint()))
            return True
        except:
            pass

    @property
    def title(self):
        try:
            return win32gui.GetWindowText(self.hwnd)
        except:
            return ''


mod_lookup = {
    "ctrl": win32con.MOD_CONTROL, "alt": win32con.MOD_ALT,
    "win": win32con.MOD_WIN, "shift": win32con.MOD_SHIFT,
}

vk_lookup = {
    "up": win32con.VK_UP, "down": win32con.VK_DOWN,
    "left": win32con.VK_LEFT, "right": win32con.VK_RIGHT,

    "pgup": win32con.VK_PRIOR, "pgdown": win32con.VK_NEXT,
    "home": win32con.VK_HOME, "end": win32con.VK_END,
    "insert": win32con.VK_INSERT, "delete": win32con.VK_DELETE,

    "tab": win32con.VK_TAB, "escape": win32con.VK_ESCAPE, "backspace": win32con.VK_BACK,
    "enter": win32con.VK_RETURN, "space": win32con.VK_SPACE,

    "f1": win32con.VK_F1, "f2": win32con.VK_F2, "f3": win32con.VK_F3, "f4": win32con.VK_F4,
    "f5": win32con.VK_F5, "f6": win32con.VK_F6, "f7": win32con.VK_F7, "f8": win32con.VK_F8,
    "f9": win32con.VK_F9, "f10": win32con.VK_F10, "f11": win32con.VK_F11, "f12": win32con.VK_F12,
    "f13": win32con.VK_F13, "f14": win32con.VK_F14, "f15": win32con.VK_F15, "f16": win32con.VK_F16,
    "f17": win32con.VK_F17, "f18": win32con.VK_F18, "f19": win32con.VK_F19, "f20": win32con.VK_F20,
    "f21": win32con.VK_F21, "f22": win32con.VK_F22, "f23": win32con.VK_F23, "f24": win32con.VK_F24
}


class KeyBind(namedtuple('KeyBind', ['id', 'mods', 'virt_keys'])):
    __slots__ = ()

    def register(self, hwnd):
        return windll.user32.RegisterHotKey(hwnd, self.id, self.mods, self.virt_keys)

    def unregister(self, hwnd):
        windll.user32.UnregisterHotKey(hwnd, self.id)


class WinMethods:
    def __init__(self, msg_processor=None):
        self.monitors = []
        self.find_monitors()

        self.hwnd_to_win = {0: None}

        if msg_processor is None:
            def msg_processor(m):
                pass

        self.msg_processor = msg_processor
        self.spy = None
        self.hotkeys = []

        self.msg_type_to_action = {
            win32con.HSHELL_WINDOWCREATED: 'new_win',
            win32con.HSHELL_WINDOWDESTROYED: 'close_win',
            win32con.WM_HOTKEY: 'hotkey',
            32772: 'focus_win',
        }

        self.shell = win32com.client.Dispatch("WScript.Shell")

    def _dim_from_monitor(self, rect):
        left_x, top_y, right_x, bot_y = rect
        return Dims(left_x, top_y, right_x - left_x, bot_y - top_y)

    def find_monitors(self):
        enumed_displays = win32api.EnumDisplayMonitors()
        self.monitors = [(handle, self._dim_from_monitor(rect)) for
                         handle, _, rect in enumed_displays]

        xs, ys = [], []
        for _, _, r in enumed_displays:
            xs.extend([r[0], r[2]])
            ys.extend([r[1], r[3]])
        self.monitor_bbox = [min(xs), min(ys), max(xs), max(ys)]

    def monitor_from_hwnd(self, hwnd):
        try:
            handle = win32api.MonitorFromWindow(hwnd, win32con.MONITOR_DEFAULTTONEAREST)
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
                new_win = WinWin(hwnd, self.shell)
                if new_win.title in BANNED_WINDOW_TITLES:
                    return
                self.hwnd_to_win[hwnd] = new_win
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
        try:
            win32api.SetCursorPos((dims.midpoint()))
        except:
            pass

    def add_hotkey(self, key_combo):
        hk_id = len(self.hotkeys) + 1

        mods = 0
        vk = 0
        split_keys = key_combo.split('+')

        for k in split_keys:
            if k in mod_lookup:
                mods += mod_lookup[k]
            elif k in vk_lookup:
                vk = vk_lookup[k]
            else:
                vk = ord(k.upper())

        self.hotkeys.append(KeyBind(hk_id, mods, vk))
        return hk_id

    def unbind_hotkeys(self):
        spy_hwnd = self.spy.hwnd
        for hk in self.hotkeys:
            hk.unregister(spy_hwnd)

    def _intercept_msgs(self):
        self.spy = WinTaskIcon()
        spy_hwnd = self.spy.hwnd

        for hk in self.hotkeys:
            hk.register(spy_hwnd)

        msg = self.spy.get_msg()
        while msg:
            # process msg
            pass_it_on = True

            lparam = msg[1][2]
            hwnd = msg[1][3]
            # point = msg[1][5]
            if msg[1][1] == win32con.WM_HOTKEY:
                action_hint = lparam
            elif lparam in self.msg_type_to_action:
                action_hint = self.msg_type_to_action[lparam]
            else:
                pass_it_on = False
            if pass_it_on:
                monitor_i = self.monitor_from_hwnd(hwnd)
                self._handle_msg((action_hint, hwnd, monitor_i))
            msg = self.spy.get_msg()

    def _handle_msg(self, msg):
        msg_type, hwnd = msg[0], msg[1]
        if msg_type == 'new_win':
            if hwnd not in self.hwnd_to_win:
                self.hwnd_to_win[hwnd] = WinWin(hwnd, self.shell)
            else:
                return
        elif msg_type in ['close_win', 'focus_win']:
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
        try:
            # doesn't play nice if blackbox is running.. lol
            win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, (self.hwnd, 0))
        except:
            pass

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
