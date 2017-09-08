import bbwm.drawing as bb_draw
import bbwm.core as bb_core
import bbwm.win_api as bb_api

import tkinter as tk


if __name__ == '__main__':
    # config
    c = bb_core.Config()

    # backend
    desktop = bb_core.Dims(0, 0, 800, 450)
    ws = bb_core.Workspace(desktop)

    # gui
    root = tk.Tk()
    icon = bb_api.WinMethods()
    TD = bb_draw.TestDraw(root, desktop, c, icon)

    # keybinds
    api = bb_api.TestBinds(ws, TD)

    # run it
    root.mainloop()
