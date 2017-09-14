# requirements
keyboard at least 0.11.0

# tofo

need to be able to switch the scheme on the fly, which means recomputing all spaces
equally spaced
want to do - activate shortcut - lists indices over all your currently tiled windows 
hit index and switcheroo

so.. default add win to tile > can rearrange all at once
add "workspace" -> the partition gets its own tiling scheme

## mayb?
tabs w/in partitions

how do i do equal splits and constraints.. 
for 1st one i can handle it in tiling scheme

# gotta do
actual gui / window dec

changing partition schemes on the fly / promoting partitions to workspaces
using gui to edit split ratio
    this will require me to remove root.overrideredirect(True) temporarily
		maybe not actually
    traverse and find all splits, then drawfun needs to take split as input and keep track of it in order to reset?.. so traverse to get all parents w/ non-empty splits

more partition schemes..
multiple workspaces