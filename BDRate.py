#!/usr/bin/env python
import os
import sys
import re
import csv
import argparse
import numpy as np
from collections import namedtuple

DEBUG = 1

OneTestPoint = namedtuple('TestPoint', ['qp', 'fps', 'bit_rate',
                                        'psnr_y', 'psnr_u', 'psnr_v'])


def BDRate(PSNR1, BR1, PSNR2, BR2):
    lBR1 = np.log(BR1)
    p1 = np.polyfit( PSNR1, lBR1, 3)

    lBR2 = np.log(BR2)
    p2 = np.polyfit( PSNR2, lBR2, 3)

    min_int = max(min(PSNR1), min(PSNR2))
    max_int = min(max(PSNR1), max(PSNR2))

    # find integral
    p_int1 = np.polyint(p1)
    p_int2 = np.polyint(p2)

    int1 = np.polyval(p_int1, max_int) - np.polyval(p_int1, min_int)
    int2 = np.polyval(p_int2, max_int) - np.polyval(p_int2, min_int)

    # find avg diff
    avg_exp_diff = (int2-int1)/(max_int-min_int)
    avg_diff = (np.exp(avg_exp_diff)-1)*100

    return avg_diff


def BDPSNR(PSNR1, BR1, PSNR2, BR2):
    lBR1 = np.log10(BR1)
    p1 = np.polyfit( lBR1, PSNR1, 3)

    lBR2 = np.log10(BR2)
    p2 = np.polyfit( lBR2, PSNR2, 3)

    min_int = max(min(lBR1), min(lBR2))
    max_int = min(max(lBR1), max(lBR2))

    # find integral
    p_int1 = np.polyint(p1)
    p_int2 = np.polyint(p2)

    int1 = np.polyval(p_int1, max_int) - np.polyval(p_int1, min_int)
    int2 = np.polyval(p_int2, max_int) - np.polyval(p_int2, min_int)

    # find avg diff
    avg_diff = (int2-int1)/(max_int-min_int)

    return avg_diff


def read_results_from_csv(output_name):
    csv_name = output_name+'.csv'
    if DEBUG:
        dir = os.getcwd()
        sys.stdout.write("Reading %s\n" %(dir + os.sep + csv_name) )
    csv_file = open(csv_name, 'r')
    reader = csv.reader(csv_file, dialect='excel')
    current_dict = {}
    name_idx_dict = {'name': 0, 'qp': 1, 'fps': 2, 'bitrate': 3,
                     'psnry': 4, 'psnru': 5, 'psnrv': 6}

    for idx, item in enumerate(reader[0]):
        if item in name_idx_dict:
            name_idx_dict[item] = idx

    for row in reader[1:]:
        name = row[name_idx_dict['name']]
        if not current_dict.has_key(name):
            current_dict[name] = {}
        qp = row[name_idx_dict['qp']]
        if not current_dict[name].has_key(qp):
            current_dict[name][qp] = {}
        current_dict[name][qp] = OneTestPoint(qp,
                                              row[name_idx_dict['fps']],
                                              row[name_idx_dict['bitrate']],
                                              row[name_idx_dict['psnry']],
                                              row[name_idx_dict['psnru']],
                                              row[name_idx_dict['psnrv']])
    csv_file.close()
    return current_dict


def write_testpoint_to_csv(exe_path, result_path, TestPoint_dict):
    exe_name = ((exe_path.split(os.sep))[-1])
    result_name = '%s' %(result_path) + os.sep +'Result_%s.csv' %exe_name
    result_file = open(result_name, 'a+')
    result_file.write('name,points,qp,fps,bitrate,psnry,psnru,psnrv\n')
    for yuv_item in TestPoint_dict:
        cur_yuv = sorted(TestPoint_dict[yuv_item])
        for qp in cur_yuv:
            test_point = TestPoint_dict[yuv_item][qp]
            result_file.write('%s,%d,%d,%f,%f,%f,%f,%f\n'
                               %(yuv_item, qp,
                                 test_point.qp, test_point.fps, test_point.bit_rate,
                                 test_point.psnr_y, test_point.psnr_u, test_point.psnr_v))
    result_file.close()


def calculate_from_two_dicts(result_file, dict1, dict2):
    #here the calculation refers to https://github.com/serge-m/bjontegaard2/blob/master/bjontegaard2.m
    for name in dict1:
        if dict2.has_key(name):
            # found the the matched yuv
            PSNR1 = []
            PSNR2 = []
            UPSNR1 = []
            UPSNR2 = []
            BR1 = []
            BR2 = []

            FPS1 = []
            FPS2 = []
            for qp in dict1[name]:
                if dict2[name].has_key(qp):
                    # found the match qp
                    PSNR1.append(dict1[name][qp].psnr_y)
                    PSNR2.append(dict2[name][qp].psnr_y)

                    UPSNR1.append(dict1[name][qp].psnr_u)
                    UPSNR2.append(dict2[name][qp].psnr_u)

                    BR1.append(dict1[name][qp].bit_rate)
                    BR2.append(dict2[name][qp].bit_rate)

                    FPS1.append(dict1[name][qp].fps)
                    FPS2.append(dict2[name][qp].fps)

            if len(PSNR1) == 4:
                # have enough points to calculate
                PSNR1 = sorted(PSNR1)
                PSNR2 = sorted(PSNR2)
                UPSNR1 = sorted(UPSNR1)
                UPSNR2 = sorted(UPSNR2)

                BR1 = sorted(BR1)
                BR2 = sorted(BR2)

                avg_U_bd_diff = BDRate(UPSNR1, BR1, UPSNR2, BR2)
                avg_bd_diff = BDRate(PSNR1, BR1, PSNR2, BR2)
                avg_PSNR_diff = BDPSNR(PSNR1, BR1, PSNR2, BR2)
                avg_fps_diff = 0
                for i in range(len(FPS1)):
                    avg_fps_diff+= (FPS2[i]-FPS1[i])*100/FPS1[i]
                avg_fps_diff = avg_fps_diff/len(FPS1)
                result_file.write(str([name, avg_fps_diff, avg_bd_diff, avg_U_bd_diff])+'\n')



if __name__ == '__main__':
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-log1", nargs='?', default=None, help="log1.csv")
    argParser.add_argument("-log2", nargs='?', default=None, help="log2.csv")
    args = argParser.parse_args()

    # filename: Result_Cisco_Absolute_Power_1280x720_30_1121_EnblFsOpen.csv
    if os.path.isfile(args.log1) and os.path.isfile(args.log2):
        match_re = re.compile(r'Result_(.*).csv')
        name1 = name2 = None
        r = match_re.search(args.log1)
        if r is not None:
            name1 = (r.groups()[0])
        r = match_re.search(args.log2)
        if r is not None:
            name2 = (r.groups()[0])

        if name1 is not None and name2 is not None:
            result_file = open("Result_%s_%s.csv" %(name1, name2))
            dict1 = read_results_from_csv(name1)
            dict2 = read_results_from_csv(name2)
            calculate_from_two_dicts(result_file, dict1, dict2)
            result_file.close()









