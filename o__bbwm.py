#########
#  _     _
# | |__ | |____      ___ __ ___
# | '_ \| '_ \ \ /\ / / '_ ` _ \
# | |_) | |_) \ V  V /| | | | | |
# |_.__/|_.__/ \_/\_/ |_| |_| |_|
# 
# blackbox tiling wm

import tkinter as tk
import keyboard
import win32con, win32gui

OFF_SCREEN = 25
BORDER_OFFSET = 50
INNER_SPACING = 20

class Box():
	def __init__(self,parent,index,x,y,w,h,handle=None):
		self.parent = parent
		self.index = index
		self.children = None
		self.handle = handle
		self.x, self.y, self.w, self.h = x,y,w,h

	def __iter__(self):
		if not self.is_empty:
			for b in self.children:
				yield b
		else:
			yield self

	def __str__(self):
		return 'box @ ({:4d},{:4d})      w: {:4d} h: {:4d}    {}'.format(self.x,self.y,self.w,self.h,self.handle)

	@property
	def is_empty(self):
		return self.children is None

	def get_dims(self):
		return self.x, self.y, self.w, self.h

	def split(self,dim,length,r=0.5):
		# returns new coords along a certain direction
		# so in horizontal case, supply with x and w
		# r = 0.5 by default, returns x1 w1, x2 w2
		d1, d2 = dim, dim + int(r*length) + INNER_SPACING
		w1 = int(length * r) - INNER_SPACING
		w2 = int(length * (1-r)) - INNER_SPACING
		return [(d1,w1),(d2,w2)]

	def split_h(self,r=0.5):
		child_dims = self.split(self.x,self.w,r)
		c1 = Box(self,0,child_dims[0][0],self.y,child_dims[0][1],self.h)
		c1.handle = self.handle
		c2 = Box(self,1,child_dims[1][0],self.y,child_dims[1][1],self.h)
		self.children = [c1,c2]
		self.handle = None

	def split_v(self,r=0.5):
		child_dims = self.split(self.y,self.h,r)
		c1 = Box(self,0,self.x,child_dims[0][0],self.w,child_dims[0][1])
		c1.handle = self.handle
		c2 = Box(self,1,self.x,child_dims[1][0],self.w,child_dims[1][1])
		self.children = [c1,c2]
		self.handle = None

class Workspace():
	def __init__(self,n,W,H,daddy):
		self.dad = daddy
		self.n = n
		self.total_width, self.total_height = W, H

		self.top_box = Box(None,0,0,0,W,H)
		self.current_box = self.top_box

		self.max_truth = [[self.top_box]]
		self.cur_ind = [0,0]

		self.win_api = WindowsInterface()
		
		self.tiling_scheme = self.default_scheme
		self.tiling_scheme_count = -1

	def __str__(self):
		all_boxes = self.traverse()
		all_rows = []
		for r in range(len(self.max_truth)):
			row = ''
			for c in range(len(self.max_truth[0])):
				box = self.max_truth[r][c]
				if box in all_boxes:
					if [r,c] == self.cur_ind:
						row += '[{:2d}] '.format(all_boxes.index(box))
					else:
						row += ' {:2d}  '.format(all_boxes.index(box))
				else:
					row += ' __  '
			all_rows.append(row)
		return '\n'.join(all_rows)

	def traverse(self,box=None):
		if box is None: box = self.top_box
		tor = []
		for b in box:
			if b.is_empty:
				tor.append(b)
			else:
				tor.extend(self.traverse(b))
		return tor

	def find_all(self,child):
		# returns all r,c indices of the child
		tor_r,tor_c = [],[]
		for r in range(len(self.max_truth)):
			for c in range(len(self.max_truth[0])):
				if self.max_truth[r][c] == child:
					tor_r.append(r)
					tor_c.append(c)
		return tor_r, tor_c

	def default_scheme(self):
		if self.tiling_scheme_count < 0:
			tor = lambda : 1+1
		elif self.tiling_scheme_count == 0:
			tor = lambda : self.split_h(0.67)
		else:
			tor = lambda : self.split_v()
		self.tiling_scheme_count += 1
		return tor

	def split_h(self,r=0.5):
		self.current_box.split_h(r)
		cur_r, cur_c = self.cur_ind
		# go through all the rows and duplicate whatever is in the current column
		for r in range(len(self.max_truth)):
			self.max_truth[r].insert(cur_c+1,self.max_truth[r][cur_c])
		# then substitute new elements
		find_r, find_c = self.find_all(self.current_box)
		for i in range(len(find_r)):
			if find_c[i] == max(find_c):
				self.max_truth[find_r[i]][find_c[i]] = self.current_box.children[1]
			else:
				self.max_truth[find_r[i]][find_c[i]] = self.current_box.children[0]
		self.go_in()
		self.go_side()

	def split_v(self,r=0.5):
		self.current_box.split_v(r)
		cur_r, cur_c = self.cur_ind
		# insert new row
		self.max_truth.insert(cur_r+1,[self.max_truth[cur_r][c] for c in range(len(self.max_truth[0]))])
		# then substitute new elements
		find_r, find_c = self.find_all(self.current_box)
		for i in range(len(find_r)):
			if find_r[i] == max(find_r):
				self.max_truth[find_r[i]][find_c[i]] = self.current_box.children[1]
			else:
				self.max_truth[find_r[i]][find_c[i]] = self.current_box.children[0]
		self.go_in()
		self.go_side()


	def delet_this(self):
		p_box = self.current_box.parent
		if p_box is None: return
		new_box = p_box.children[1 - self.current_box.index]

		for c in p_box.children:
			find_r, find_c = self.find_all(c)
			for i in range(len(find_r)):
				self.max_truth[find_r[i]][find_c[i]] = p_box

		p_box.children = new_box.children
		p_box.handle = new_box.handle
		new_box.handle = None
		if not p_box.is_empty:
			for c in new_box.children:
				c.parent = p_box

		self.current_box = p_box

	def tile_window(self):
		# if self.current_box.handle is None:
		new_handle = self.win_api.get_current_win(True)
		next_tiling_action = self.tiling_scheme()
		next_tiling_action()
		self.current_box.handle = new_handle
		# self.win_api.remove_crap(self.current_box.handle)

		# self.move_window(self.current_box)
		traversal = self.traverse()
		for b in traversal:
			print(b)
			self.move_window(b)
		self.dad.draw_current_state()

	def untile_window(self):
		if self.current_box.handle is not None:
			self.win_api.add_crap_back(self.current_box.handle)
			self.win_api.return_to_og(self.current_box.handle)
		self.current_box.handle = None
		self.delet_this()
		self.tiling_scheme_count -= 1
		self.tiling_scheme_count = max(-1,self.tiling_scheme_count)
		traversal = self.traverse()
		for b in traversal:
			print(b)
			self.move_window(b)
		self.dad.draw_current_state()


	def move_window(self,box):
		if box.handle is None: return
		print('moving', box.handle)
		x,y,w,h = box.get_dims()
		x = x + BORDER_OFFSET
		y = y + BORDER_OFFSET
		self.win_api.move_win(box.handle,x,y,w,h)

	## navigation.. kinda makes sense if you think of traversal up down left right whatever
	# as being kinda in order of when things were created 

	def go_ud(self,ud):
		col_len = len(self.max_truth)
		to_check = [(self.cur_ind[0] + ud*i)%col_len for i in range(1,col_len)]
		filt = [i for i in to_check if self.max_truth[i][self.cur_ind[1]] != self.current_box and\
		 		self.max_truth[i][self.cur_ind[1]].is_empty]
		if len(filt) > 0:
			self.cur_ind[0] = filt[0]
			self.current_box = self.max_truth[self.cur_ind[0]][self.cur_ind[1]]
			self.dad.draw_current_state()
			if self.current_box.handle is not None:
				self.win_api.focus_win(self.current_box.handle)

	def go_lr(self,lr):
		row_len = len(self.max_truth[self.cur_ind[0]])
		to_check = [(self.cur_ind[1] + lr*i)%row_len for i in range(1,row_len)]
		filt = [i for i in to_check if self.max_truth[self.cur_ind[0]][i] != self.current_box and\
		 		self.max_truth[self.cur_ind[0]][i].is_empty]
		if len(filt) > 0:
			self.cur_ind[1] = filt[0]
			self.current_box = self.max_truth[self.cur_ind[0]][self.cur_ind[1]]
			self.dad.draw_current_state()
			if self.current_box.handle is not None:
				self.win_api.focus_win(self.current_box.handle)


	def go_up(self):
		self.go_ud(-1)
	def go_down(self):
		self.go_ud( 1)
	def go_left(self):
		self.go_lr(-1)
	def go_right(self):
		self.go_lr( 1)

	def go_out(self):
		if self.current_box.parent is not None:
			self.current_box = self.current_box.parent
			# print('you went out to',self.current_box)

	def go_in(self):
		if not self.current_box.is_empty:
			self.current_box = self.current_box.children[0]
			# print('you went in to',self.current_box)

	def go_side(self):
		if self.current_box.parent is not None:
			self.current_box = self.current_box.parent.children[1 - self.current_box.index]
			# print('you went l/r to',self.current_box)


class WindowsInterface():
	def __init__(self):
		self.backup_positions = {}

	def get_current_win(self,first_time=False):
		handle = win32gui.GetForegroundWindow()
		if first_time:
			l,t,r,b = win32gui.GetWindowRect(handle)
			x,y,w,h = l, t, r-l, b-t
			self.backup_positions[str(handle)] = [x,y,w,h]
		return handle

	def focus_win(self,handle):
		try:
			win32gui.SetForegroundWindow(handle)
		except:
			pass

	def return_to_og(self,hwnd):
		if str(hwnd) in self.backup_positions:
			x,y,w,h = self.backup_positions[str(hwnd)] 
			win32gui.MoveWindow(hwnd,x,y,w,h,True)	

	def remove_crap(self,hwnd):
		pass
		# style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
		# style -= win32con.WS_CAPTION 
		# win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)

	def move_win(self,hwnd,x,y,w,h):
		win32gui.MoveWindow(hwnd,x,y,w,h,True)

	def add_crap_back(self,hwnd):
		pass
		# style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
		# style += win32con.WS_CAPTION 
		# win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)

# hwnd = win32gui.FindWindow(None, 'MilkDrop 2')
# # ""borderless window""
# style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
# style -= win32con.WS_CAPTION 
# win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
# win32gui.MoveWindow(hwnd,25,25,500,500,True)

def main():
	root = tk.Tk()
	root.wm_attributes("-topmost", True)
	# root.attributes("-toolwindow", 1)
	# root.wm_attributes("-disabled", True)
	root.wm_attributes("-transparentcolor", "blue")
	root.overrideredirect(True)
	fun = ScreenDraw(root, )

	keyboard.add_hotkey('ctrl+alt+space', fun.draw_current_state)
	keyboard.add_hotkey('ctrl+alt+up', fun.workspace.go_up)
	keyboard.add_hotkey('ctrl+alt+down', fun.workspace.go_down)
	keyboard.add_hotkey('ctrl+alt+left', fun.workspace.go_left)
	keyboard.add_hotkey('ctrl+alt+right', fun.workspace.go_right)

	keyboard.add_hotkey('ctrl+alt+z', fun.workspace.tile_window)
	keyboard.add_hotkey('ctrl+alt+x', fun.workspace.untile_window)
	keyboard.add_hotkey('ctrl+alt+a', fun.workspace.split_h)
	keyboard.add_hotkey('ctrl+alt+s', fun.workspace.split_v)
	# keyboard.add_hotkey('ctrl+alt+z', fun.workspace.split_h) # tile window h
	# keyboard.add_hotkey('ctrl+alt+x', fun.workspace.split_v) # tile window v
	# keyboard.add_hotkey('ctrl+alt+c', fun.workspace.delet_this) # untile window

	# keyboard.add_hotkey('ctrl+alt+x', fun.clear_screen) # untile window
	keyboard.add_hotkey('ctrl+alt+q', root.destroy)
	root.mainloop()	

def test_ws():
	test_ws = Workspace(1,1280,720)
	# traversal = test_ws.traverse()
	# print('traverse!!')
	# for b in traversal:
	# 	print(b)
	print(test_ws)

	print('split h!!')
	test_ws.split_h()
	# print('traverse!!')
	# traversal = test_ws.traverse()
	# for b in traversal:
	# 	print(b)
	print(test_ws)
	print('split v!!')
	test_ws.split_v()
	print(test_ws)
	print('split h!!')
	test_ws.split_h()
	print(test_ws)
	print('split v!!')
	test_ws.split_v()
	print(test_ws)
	print('split h!!')
	test_ws.split_h()
	print(test_ws)

if __name__ == '__main__':
	main()
