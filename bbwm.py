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
	each container is a rectangle of screen space
	also specifies how next container will be partitioned
	"""

	def __init__(self,parent,x,y,w,h,hv=0,r=1): 
		# vh - default split for new containers (0 for horizontal 1 for vertical, r - ratio of split
		# hv is either 0 or 1, r is any positive rational number :^) 
		self.parent = parent # the workspace
		self.contents = []
		self.window = None
		self.x, self.y, self.w, self.h = x, y, w, h
		self.hv, self.r = hv, r
		self.index = 0

	def __str__(self):
		tor = "container @({0},{1}) w: {2} h: {3}".format(self.x, self.y, self.w, self.h)
		return tor

	def __iter__(self):
		for sc in self.contents:
			yield sc

	def __len__(self):
		return len(self.contents)

	def is_empty(self):
		return self.contents == []

	def add_window(self,window):
		window.resize(self.x,self.y,self.w,self.h)
		self.window = window

	def resize(self, x, y, w, h): 
		#print("resizing from {0},{1},{2},{3} to {4},{5},{6},{7}".format(self.x, self.y, self.w, self.h , x, y, w, h))
		self.x, self.y, self.w, self.h  = x, y, w, h

	def reflow(self,hv = None):
		if hv is None: hv = self.hv
		if self.r == 1:
			new_r = len(self) 
		else: 
			if len(self) != 1:
				new_r = self.r
			else:
				new_r = 1
		if hv == 0:
			new_w, new_h = self.w // new_r, self.h
			new_x, new_y = self.x + self.w,self.y
		else:
			new_w, new_h = self.w, self.h // new_r
			new_x, new_y = self.x,self.y + self.h

		neww_w, neww_h = new_w, new_h
		
		for i in reversed(range(self.__len__())):
			# resize all subcontainers according to split ratio
			new_x -= new_w * (1-hv)
			new_y -= new_h * hv
			self.contents[i].resize(new_x,new_y,neww_w,neww_h)
			neww_w = self.w - new_w * (1-hv)
			neww_h = self.h - new_h * hv
			# first part is subtract new part


	def get_dims(self):
		return self.x, self.y, self.w, self.h

	def get_parent(self):
		return self.parent

	def add_sub(self,hv = None,hvn=0,r=1): # hv allows to partition non-default way if passed
		new_sub = Container(self,-1,-1,-1,-1,hvn,r)
#		self.parent.add_container(new_sub)
		self.contents.append(new_sub)
		self.reflow(hv)
		return self.contents

	def p_add_sub(self,hv = None,hvn=0,r=1): #you're becoming a new parent
		if not self.is_empty():
			self.add_sub(hv,hvn,r)
		else:
			self.add_sub(hv,hvn,r)
			self.add_sub(hv,hvn,r)

	def add_container(self,container):
		self.contents.append(container)

	def traverse_container(self,contents=None):
		if contents is None: contents = self.contents
		tor = []
		for c in contents:
			if c.is_empty():
				#print(c.__str__())
				tor.append(c)
			else:
				tor.extend(self.traverse_container(c))
		return tor


class Workspace():
	"""
	used to represent a virtual screen
	contains windows in set positions that can be moved around
	attributes include - max height, max width, number, partition style
	"""
	def __init__(self,n,W,H):
		self.n = n
		self.W, self.H = W, H
		self.p_style = DEFAULT_PARTITION
		self.main_container = Container(self,0,0,W,H,r=3)
		self.main_container.add_sub(0)
		self.traverse = self.main_container.traverse_container
		self.style = PartitionStyle()

	def __str__(self):
		tor = "Workspace #{0} W: {1} H: {2}".format(self.n,self.W,self.H) + "\n"
		tempa = [[0 for x in range(self.W)] for x in range(self.H)] 
		foot = "-"*self.W+"\n"
		ci = 0
		for c in self.traverse():
			foot += str(ci) + " - " + c.__str__() + "\n"
			tempa = self.draw_help(tempa,c,ci)
			ci += 1

		for j in range(self.H):
			for i in range(self.W):
				tor = tor + str(tempa[j][i])
			tor = tor + "\n"

		return tor + foot

	def __len__(self):
		return len(self.traverse())

	def draw_help(self,a,c,n):
		x,y,w,h = c.get_dims()
		for j in range(h):
			for i in range(w):
				#print(x+i,y+j)
				try:
					a[y+j][x+i] = n
				except:
					print('{2} is out of range at ({0},{1})'.format(y+j,x+i,n))
		return a

	def add_container(self,p=True,where=-1,hv=None,hvn=0,r=1): # adds a window and tiles it, with the possiblity of tiling in new creative way : )
		t = self.traverse()
		if p:
			t[where].get_parent().add_sub(hv,hvn,r)
		else:
			t[where].p_add_sub(hv,hvn,r)

	def add_next(self):
		p, hv, rn = self.style.get_next()
		self.add_container(p,-1,hvn=hv,r=rn)

class PartitionStyle():
	"""
	used to represent a method of styling
	basically contains p, hv, and r for certain levels
	"""
	def __init__(self,style=None):
		if style is None: # default style
			self.style = [[True,0,3],[False,1,1]] # rStack for ex
		else:
			self.style = style
		self.index = 0

	def get_next(self):
		try:
			tor = self.style[self.index]
			self.index += 1
		except:
			tor = self.style[-1]
		return tor




if __name__=='__main__':
	testwin = Window("lol",1,2,3,4)
	#print(testwin)

	testworkspace = Workspace(1,12,6)
	#print(testworkspace)

	testcontainer = Container(testworkspace,0,0,6,3)
	#print(testcontainer.get_dims())
	
	#testworkspace.add_container()
	#print(testworkspace)	
	#for i in range(2):
	#	testworkspace.add_container(where=-1,hv=i)
	#	print(testworkspace)

	#testworkspace.add_container(where=0)
	##print(testworkspace)
	##testworkspace.add_container(where=0)
	##print(testworkspace)
	#testworkspace.add_container(p=False,where=1,hv=1)
	##print(testworkspace)	
	#testworkspace.add_container(p=True,where=1,hv=1)
	##print(testworkspace)	
	#testworkspace.add_container(p=False,where=3,hv=0)
	##print(testworkspace)
	#testworkspace.add_container(p=False,where=4,hv=1)
	# dont do something like this - testworkspace.add_container(p=True,where=0,hv=1)
	#print(testworkspace)
	testworkspace.add_next()
	print(testworkspace)
	testworkspace.add_next()
	print(testworkspace) # sad horns play

#####################################################
#
# Sweet, it works
#
# Workspace #1 W: 12 H: 6
# 000000001111
# 000000001111
# 000000002222
# 000000002222
# 000000003344
# 000000003355
# ------------
# 0 - container @(0,0) w: 6 h: 6
# 1 - container @(6,0) w: 6 h: 2
# 2 - container @(6,2) w: 6 h: 2
# 3 - container @(6,4) w: 3 h: 2
# 4 - container @(9,4) w: 3 h: 1
# 5 - container @(9,5) w: 3 h: 1