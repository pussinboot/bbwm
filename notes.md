tofo

# first redo it
not a binary tree but node structure.. all children of a big partition will have same tiling scheme

need to be able to switch the scheme on the fly, which means recomputing all spaces
so 2 sets of data for each node.. where it is in the tree as well as relative transformation taken so it can be chained together

so.. default add win to tile > can rearrange all at once
add "workspace" -> the partition gets its own tiling scheme
splits.. wherever og window was has been split..

# then actually tiling

get reliable win api hooking DONE
need to register a shellhook to receive messages about closed / new windows? DONE
this should be added to the tk "window" DONE
main bbwm fun needs to tie together the tiling logic with windows & the gui but they should remain (mostly) independent KINDA DONE

# gotta do
move btwn windows
actual gui / window dec & placement

ok.. so it kinda works but 
still need swaps

# mayb?
tabs w/in partitions

how do i do equal splits and constraints.. 
for 1st one i can handle it in tiling scheme
