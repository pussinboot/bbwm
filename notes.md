tofo

# first redo it
not a binary tree but node structure.. all children of a big partition will have same tiling scheme

need to be able to switch the scheme on the fly, which means recomputing all spaces
so 2 sets of data for each node.. where it is in the tree as well as relative transformation taken so it can be chained together

so.. default add win to tile > can rearrange all at once
add "workspace" -> the partition gets its own tiling scheme
splits.. wherever og window was has been split..

2 untile u just merge partitions 

# then actually tiling

get reliable win api hooking

# mayb?
tabs w/in partitions



# nnn
so split info goes into parent when a split occurs

fix untile
    make sure to account for if children > 2..
    how do i do equal splits and constraints.. 
    for 1st one i can handle it in tiling scheme
