#!/usr/bin/env python
import os
import sys
import re
import csv
import glob
import datetime
import argparse
import subprocess
import numpy
import matplotlib.pyplot as plt
import __init__, config, CodecUtil
from BDRate import calculate_from_two_dicts, OneTestPoint, write_testpoint_to_csv

DEBUG = 0
PERFORMANCE_ONLY = False
SKIP_ENCODING = False
TEST_JM = config.JM_TEST

def encode_one_yuv(exe_path, one_yuv, usage_type=0, qp=24):
    name = ((one_yuv.split(os.sep))[-1])

    width, height, frame_rate = CodecUtil.get_resolution_from_name(name)
    if frame_rate == 0:
        frame_rate = 30

    # encoding
    current_path = os.getcwd()
    os.chdir(exe_path)
    print("current path is %s\n" %exe_path)

    if not SKIP_ENCODING:
        if TEST_JM:
            bs_name, log_name = CodecUtil.call_jm_encoder(one_yuv, usage_type, width, height, qp, ' -p IDRPeriod=1 -p LevelIDC=51 ')
        else:
            bs_name, log_name = CodecUtil.call_encoder_qp(one_yuv, usage_type, width, height, qp, ' -threadIdc 1  ')
    else:
        bs_name  = one_yuv.split(os.sep)[-1] + '_br' + str(qp) + '.264'
        log_name = one_yuv.split(os.sep)[-1] + '_br' + str(qp) + '.log'
    #deal with log file
    fps = CodecUtil.encoder_log_file(log_name)

    if not PERFORMANCE_ONLY:
        # decoding
        rec_yuv = bs_name+'_dec.yuv'
        if TEST_JM:
            CodecUtil.jm_decode(bs_name, rec_yuv)
        else:
            CodecUtil.decode(bs_name, rec_yuv)

        # psnr ing
        frame_num, bitrate, psnr_y, psnr_u, psnr_v = CodecUtil.PSNRStaticd(width, height, one_yuv, rec_yuv,
                                                         rec_yuv+'.log', bs_name, frame_rate)

        file_size = os.path.getsize(bs_name)
        current_test_point = OneTestPoint(width, height, frame_rate, frame_num, qp, file_size, fps, bitrate, psnr_y, psnr_u, psnr_v)

        os.remove(rec_yuv)
    else:
        current_test_point = OneTestPoint(width, height, frame_rate, 0, qp, 0, fps, 0, 0, 0, 0)
        if DEBUG==0:
            os.remove(bs_name)
            os.remove(log_name)

    os.chdir(current_path)
    return current_test_point


def process_one_exe(exe_path, yuv_list, usage_type):
    TestPoint_dict = {}

    for one_yuv in yuv_list:
        for qp in [24,]:#[22, 27, 32, 37]:
            result = encode_one_yuv(exe_path, one_yuv, usage_type, qp)
            yuv_name = ((one_yuv.split(os.sep))[-1])
            if not TestPoint_dict.has_key(yuv_name):
                TestPoint_dict[yuv_name] = {}
            if not TestPoint_dict[yuv_name].has_key(qp):
                TestPoint_dict[yuv_name][qp] = {}
            TestPoint_dict[yuv_name][qp] = result


    write_testpoint_to_csv(exe_path, os.getcwd(), TestPoint_dict)

    return TestPoint_dict


if __name__ == '__main__':
    argParser = argparse.ArgumentParser()
    argParser.add_argument("exepath", nargs='+', help="exe path, you can specify multiple logpath seperated by space")
    argParser.add_argument("-yuvpath", nargs='?', default=None, help="yuv path")
    argParser.add_argument("-usagetype", nargs='?', default=None, help="camera=0 or screen=1")
    argParser.add_argument("-performance_only", nargs='?', default=None, help="skip_psnr_test")
    argParser.add_argument("-skip_encoding", nargs='?', default=None, help="skip_psnr_test")
    args = argParser.parse_args()

    usage_type = 0
    if args.usagetype is not None:
        usage_type = args.usagetype

    if usage_type == 0:
        default_yuv_path = __init__.CAMERA_SEQ_PATH
    else:
        default_yuv_path = __init__.SCREEN_SEQ_PATH
    if DEBUG:
        default_yuv_path = __init__.TMP_FOLDER
    if args.yuvpath is not None:
        default_yuv_path = args.yuvpath

    if args.performance_only is not None:
        PERFORMANCE_ONLY = True

    if args.skip_encoding is not None:
        SKIP_ENCODING = True

    sys.stdout.write('Current TestSet is %s\n' %default_yuv_path)
    yuv_list = []
    for f in glob.glob(default_yuv_path + os.sep + '*.yuv'):
        yuv_list.append(f)

    dict_list = []
    for one_exe_path in args.exepath:
        if not os.path.isdir(one_exe_path):
            sys.stdout.write('Invalid exepath %s\n' %one_exe_path)
        else:
            sys.stdout.write('current exe path is %s\n' %one_exe_path)
            dict = process_one_exe(one_exe_path, yuv_list, usage_type)
            dict_list.append(dict)

    if not PERFORMANCE_ONLY:
        sys.stdout.write('Begin compare.. \n')
        for i in range(len(args.exepath)):
            if i==0:
                continue
            name0 = ((args.exepath[0].split(os.sep))[-1])
            name1 = ((args.exepath[i].split(os.sep))[-1])

            current_path = os.getcwd()
            os.chdir(args.exepath[i])
            result_file = open("Result_%s_%s.csv" %(name0, name1), 'w')
            calculate_from_two_dicts(result_file, dict_list[0], dict_list[i])
            result_file.close()
            os.chdir(current_path)


















