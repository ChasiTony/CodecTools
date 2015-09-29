# CodecTools

local settings are in config.py

============
Tool Sets
============

DownsamplerTest.py
    argParser.add_argument("exepath", nargs='?', help="exe path")
    argParser.add_argument("-jsvm", nargs='?', help="jsvm downconvert path")
    argParser.add_argument("-yuvpath", nargs='?', default=None, help="yuv path")
    argParser.add_argument("-usagetype", nargs='?', default=None, help="camera=0 or screen=1")
    argParser.add_argument("-downscale", nargs='?', default=4, help="downscale")
    argParser.add_argument("-out", nargs='?', default=None, help="set out path")
