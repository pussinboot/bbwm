~~~
|        |        |  |  |
|        |______  |__|__|
|        |      |
|______  |______| _______
|      |          |  |  |
|______|          |  |  |
~~~

`bbwm` is a tiling window manager that works on windows (for now)

### key features

- window tiling with multiple workspace/display support
- slick non-intrusive ui and sane ux

### requirements

- autohotkey
- pywin32

### instructions

1. install requirements
2. run `block.ahk`
3. run `neo_bbwm.py`

### keybinds

~~~
win + z - tile focused window into a new/empty partition
win + x - untile current window/partition
win + c - tile focused window into current partition (buggy)

win + a - split horizontally
win + s - split vertically
win + d - switch between horizontal or vertical
win + d (2x) - flip ratio

win + arrow keys - move among tiled windows
ctrl + win + arrow keys - swap partitions
win + delete/home/end/page down - jump across displays
win + 1/2/3 - switch workspaces

win + f - enter resize mode
-- use arrow keys or the mouse to resize partitions
-- pressing escape or any other key combo exits

win + w - open quick jump menu
-- hints let you jump across windows or displays
-- up/down to choose a tiled window, press enter to switch to it
-- pressing escape or any other key combo exits

win + q - open partition menu
-- not ready for prime time

~~~
