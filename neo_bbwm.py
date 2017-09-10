import bbwm.drawing as bb_draw
import bbwm.core as bb_core
import bbwm.win_api as bb_api

import tkinter as tk


if __name__ == '__main__':
    # config
    c = bb_core.Config()

    # backend
    wee = bb_api.WinMethods()
    desktop = wee.monitors[0][1].get_ws_dims(c)

    # gui
    root = tk.Tk()
    root.wm_attributes("-topmost", True)
    root.wm_attributes("-transparentcolor", "#0DEAD0")
    root.overrideredirect(True)

    # TD = bb_draw.TestDraw(root, desktop, c)
    BBD = bb_draw.BBDraw(root, desktop, c)

    # keybinds
    # api = bb_api.TestBinds(ws, TD)
    api = bb_api.WinBinds(wee, BBD)

    # run it
    root.mainloop()


# remember
# ctrl+alt+q quit
# ctrl+alt+c draw_parts
# ctrl+alt+r print workspace