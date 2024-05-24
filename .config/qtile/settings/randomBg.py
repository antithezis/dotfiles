#!/usr/bin/env python

import glob
import random
import os


files = glob.glob("/home/antithezis/images/wallpaper/*.jpg, *.png, *jpeg")
random.shuffle(files)
command = "feh --no-fehbg --bg-fill " + files[0] + " " + files[1]
os.system(command)
