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

DEFAULT_PARTITION = "lol" # partitions will be a cool data type that represent the tiling "style"
# specify the major partitioning/ratios and a default subpartitioning method
# ex
# [[(h, 3)] (v, 1)] # h = 0, v = 1
# first window takes up whole screen
# second window takes up rightmost third of screen ()
# subsequent windows evenly split the rightmost third in height

class Window():
	"""
	used to represent a window
	attributes include - top positions for x & y, width, height, current workspace, current monitor, win32 handle
	"""
	# make the window object when a window is going to be tiled for the first time
	def __init__(self,handle,x=-1,y=-1,w=-1,h=-1): 
		self.handle = handle
		self.x, self.y, self.w, self.h  = x, y, w, h

	def __str__(self):
		return self.handle + " @({0},{1}) w: {2} h: {3}".format(self.x, self.y, self.w, self.h)

	def resize(self, x, y, w, h): 
		self.x, self.y, self.w, self.h  = x, y, w, h

# reason for seperate containers and windows is in case where you want to have one window take up the space you usually would've gotten if you reflowed once more
# aka in standard ex if you had 3 windows, 1 on 2/3rd left, 2 & 3 each taking up half of the remaining third, if you wanted 3 to take up 2/3rd of the third

class Container():
	"""
	each container contains windows or subcontainers
	also specifies how it will be partitioned
	"""

	def __init__(self,parent,window,x,y,w,h,hv=0,r=1): 
		# vh - default split for new containers (0 for horizontal 1 for vertical, r - ratio of split
		# hv is either 0 or 1, r is any positive rational number :^) 
		self.parent = parent # the workspace
		self.contents = []
		self.x, self.y, self.w, self.h = x, y, w, h
		self.hv, self.r = hv, r

	def resize(self, x, y, w, h): 
		self.x, self.y, self.w, self.h  = x, y, w, h

	def get_dims(self):
		return self.x, self.y, self.w, self.h

	def add_sub(self,window,hv = None): # hv allows to partition non-default way if passed
		if hv is None: hv = self.hv
		if self.r == 1:
			new_r = len(self.contents)+1
		else:
			new_r = self.r
		if hv == 0:
			new_w, new_h = self.w - self.w // new_r, self.h
		else:
			new_w, new_h = self.w, self.h - self.h // new_r
		self.resize(self.x,self.y,new_w,new_h)
		new_sub = Container(self.parent,self.x+new_w*(1-hv),self.y+new_h*hv,self.w-new_w*(1-hv),self.h-new_h*hv)
		#fug
		self.parent.add_container(new_sub)



class Workspace():
	"""
	used to represent a virtual screen
	contains windows in set positions that can be moved around
	attributes include - max height, max width, number, partition style
	"""
	def __init__(self,n,W,H):
		self.n = n
		self.containers = [] # first version will do everything with arrays because they are ez, will see about more efficient structures later
		self.W, self.H = W, H
		self.p_style = DEFAULT_PARTITION
		self.main_container = Container(self,None,0,0,W,H)

	def __str__(self):
		# print out a cute picture
		tempa = [[0 for x in range(self.W)] for x in range(self.H)] 
		tor = "Workspace #{0} W: {1} H: {2}".format(self.n,self.W,self.H) + "\n"
		for j in range(self.H):
			for i in range(self.W):
				tor = tor + str(tempa[j][i])
			tor = tor + "\n"
		return tor

	def add_container(self,container,window,where=-1): # adds a window and tiles it, with the possiblity of tiling in new creative way : )
		self.containers.append(container)
		self.reflow(window,where)

	def reflow(self,window,where):
		self.containers[where].add_sub(window)





if __name__=='__main__':
	testwin = Window("lol",1,2,3,4)
	#print(testwin)
	testworkspace = Workspace(1,12,6)
	print(testworkspace)
	testcontainer = Container(testworkspace,testwin,0,0,6,3)
	print(testcontainer.get_dims())
	testworkspace.add_container(testcontainer,testwin)