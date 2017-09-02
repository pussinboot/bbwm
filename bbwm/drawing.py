import tkinter as tk


class TestDraw:
    def __init__(self, root, base_dims, config):
        WIDTH, HEIGHT = base_dims.w, base_dims.h

        self.c = config

        self.root = root
        self.root.title('bbwm test')

        self.canvas = tk.Canvas(self.root, width=WIDTH, height=HEIGHT, bg="salmon")
        self.canvas.pack()

    def get_bbox(self, dims):
        x, y, w, h = dims.x, dims.y, dims.w, dims.h
        lx, rx = x + self.c.INNER_SPACING_X, x + w - self.c.INNER_SPACING_X
        ty, by = y + self.c.INNER_SPACING_Y, y + h - self.c.INNER_SPACING_Y
        return lx, ty, rx, by

    def draw_border(self, dims, highlight=False):
        if highlight:
            outline = self.c.BORDER_HIGHLIGHT_COLOR
        else:
            outline = self.c.BORDER_COLOR

        w = max(min(self.c.INNER_SPACING_X, self.c.INNER_SPACING_Y) - 2, 2)
        self.canvas.create_rectangle(self.get_bbox(dims), outline=outline, width=w)



class BBDraw:
    def __init__(self, root, workspace):
        self.root = root
        self.max_width, self.max_height = root.winfo_screenwidth(), root.winfo_screenheight()
        w, h, x, y = self.max_width + 2*OFF_SCREEN, self.max_height + 2*OFF_SCREEN, -OFF_SCREEN, -OFF_SCREEN
        root.geometry('%dx%d+%d+%d' % (w, h, x, y))
        self.max_width, self.max_height = self.max_width - BORDER_OFFSET - 2*OFF_SCREEN, self.max_height - BORDER_OFFSET - 2*OFF_SCREEN

        self.canvas = tk.Canvas(root,width=w,height=h,bg="blue")
        self.canvas.pack()

        self.current_drawings = []

        self.workspace = Workspace(1,self.max_width,self.max_height,self)

        # self.draw_border(0,0,self.max_width//2-BORDER_OFFSET//2,self.max_height)
        # self.draw_border(self.max_width//2+BORDER_OFFSET//2,0,self.max_width//2-BORDER_OFFSET//2,self.max_height)



    def draw_border(self,left_x,top_y,w,h,current):
        if current:
            outline = 'gray'
        else:
            outline = 'black'
        left_x, top_y = OFF_SCREEN + BORDER_OFFSET + left_x, OFF_SCREEN + BORDER_OFFSET + top_y
        nr = self.canvas.create_rectangle(left_x, top_y, left_x + w, top_y + h,tags="border",
                                          outline=outline,width=5)#, fill='gray',stipple='gray12')
        self.current_drawings.append(nr)

    def clear_screen(self):
        for cd in self.current_drawings:
            self.canvas.delete(cd)

    def draw_current_state(self):
        bbbbb = '=' * 5 * len(self.workspace.max_truth[0])
        print(bbbbb)
        print(self.workspace)
        # print(len(self.workspace.max_truth))
        # print(len(self.workspace.max_truth[0]))
        self.clear_screen()
        for b in self.workspace.traverse():
            # print(b)
            x,y,w,h = b.get_dims()
            self.draw_border(x,y,w,h,b==self.workspace.current_box)
        # x,y,w,h = self.workspace.current_box.get_dims()    
        # self.draw_border(x,y,w,h,True)
        self.root.after(1000,self.clear_screen)
