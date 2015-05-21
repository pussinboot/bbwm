#########
#  _     _
# | |__ | |____      ___ __ ___
# | '_ \| '_ \ \ /\ / / '_ ` _ \
# | |_) | |_) \ V  V /| | | | | |
# |_.__/|_.__/ \_/\_/ |_| |_| |_|
# 
# blackbox tiling wm
# will interface with pahk "soon"

# globals (load from config file eventually)

DEFAULT_PARTITION = "lol" # partitions will be a cool data type (probably a tuple) that represent the tiling "style"


class Window():
	"""
	used to represent a window
	attributes include - top positions for x & y, width, height, current workspace, current monitor, win32 handle
	"""
	# make the window object when a window is going to be tiled for the first time
	def __init__(self,handle): 
		self.handle = handle
		self.x, self.y, self.w, self.h  = -1, -1, -1, -1 

	def set_pos(self, x, y): 
		self.x, self.y = x, y

	def set_wh(self, w, h):
		self.w, self.h = w, h

class Workplace():
	"""
	used to represent a virtual screen
	contains windows in set positions that can be moved around
	attributes include - max height, max width, number, partition style
	"""
	def __init__(self,n,W,H):
		self.n = n
		self.wins = [] # first version will do everything with arrays because they are ez, will see about more efficient structures later
		self.W, self.H = W, H
		self.p_style = DEFAULT_PARTITION

	def __str__(self):
		# print out a cute picture
		print("[]")

	def add_window(self,window,where=-1): # adds a window and tiles it, with the possiblity of tiling in new creative way : )
		self.wins.append(window)
		self.reflow()

	def reflow():
		# compute where everything should go based on the partitioning
		# first will do default ez pz ex
		nw = len(wins)
		for w in self.wins:
			w.set_wh(int(self.W/nw),self.H)
			w.set_pos() # here is where i realized i would rather do this with recursion and stopped for the day : )