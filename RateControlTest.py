#!/usr/bin/env python
import os
import sys
import re
import csv
import glob
import argparse
import subprocess
import numpy
import matplotlib.pyplot as plt

import __init__, RateControlUtil, CodecUtil
#sys.path.append(os.path.abspath('/Users/sijchen/WorkingCodes/Github/RDTest'))
from CodecUtil import calculate_psnr

from ctypes import *


DEBUG = 1

BIT_RATE_TIMEWINDOW_CAMERA = 5000
BIT_RATE_TIMEWINDOW_SCREEN = 10000
frame_skip_list = [0,1]
RC_MODE_LIST = [0,1,2,3]
MAX_BR_RATIO = 1


def copy_one_frame(orig_yuv, tar_yuv, width, height, pos):
    #gcc -c -fPIC EditAFrame.c
    #gcc -shared EditAFrame.o -o EditAFrame.so
   # EditAFrame_so = cdll.LoadLibrary('../EditAFrame.so')
   # EditAFrame_so.Processing(1, orig_yuv, tar_yuv, width, height, pos)

    print(os.getcwd())
    cmdline = str('%s 1 %s %s %d %d %d'
                % ('../EditAFrame', orig_yuv, tar_yuv, width, height, pos))
    p = subprocess.Popen(cmdline, stderr=subprocess.PIPE, shell=True)
    p.communicate()[1]



class cCurrentLog(object):
    def __init__(self):
        self.MAX_D_LAYER = 4
        self.basic_setting_match_re1 = RateControlUtil.SETTING_TYPE_RE
        self.setting_match_re = RateControlUtil.LAYER_SETTING_RE

        self.setoption_br_match = RateControlUtil.SETOPTION_BR_RE
        self.setoption_maxbr_match = RateControlUtil.SETOPTION_MAXBR_RE

        self.rc_log_match_re = RateControlUtil.RC_DEBUG_LOG_RE
        self.rc_m_log_match_re = RateControlUtil.RC_DEBUG_LOG_RE2
        self.rc_skip_frame_match_re = RateControlUtil.RC_DEBUG_SKIPLOG_RE
        self.rc_debug_match_re = RateControlUtil.RC_DEBUG_LOG_RE3

        self.name = None
        self.multi_layer_flag = False

        self.settings = []
        self.frames = [{'timestamp':[], 'frame_type':[], 'target_qp':[], 'average_qp':[], 'tid':[], 'bits':[], 'min_qp':[], 'max_qp':[]},
                       {'timestamp':[], 'frame_type':[], 'target_qp':[], 'average_qp':[], 'tid':[], 'bits':[], 'min_qp':[], 'max_qp':[]},
                       {'timestamp':[], 'frame_type':[], 'target_qp':[], 'average_qp':[], 'tid':[], 'bits':[], 'min_qp':[], 'max_qp':[]},
                       {'timestamp':[], 'frame_type':[], 'target_qp':[], 'average_qp':[], 'tid':[], 'bits':[], 'min_qp':[], 'max_qp':[]}]
        self.skip_list = []

        self.section_time = []
        self.section_rates = []
        self.total_bits = 0

        self.exceed_max_times = 0
        self.exceed_target_times = 0

        self.overall_time = []
        self.overall_rates = []
        self.overall_upper = []
        self.overall_max = []

    def check_ts(self, input):
        cur_ts = int(input)
        if cur_ts == 0 and len(self.frames[0]['timestamp'])>0:
            # ts is not valid
            cur_ts = int(1000/self.settings[-1]['frame_rate']) + self.frames[0]['timestamp'][-1]
        return cur_ts

    def add_one_frame(self, ts, r_list):
        self.frames[0]['timestamp'].append(ts)
        self.frames[0]['frame_type'].append(r_list[0])
        self.frames[0]['target_qp'].append(r_list[1])
        self.frames[0]['average_qp'].append(r_list[2])

        self.frames[0]['max_qp'].append(r_list[3])
        self.frames[0]['min_qp'].append(r_list[4])
        self.frames[0]['tid'].append(r_list[5])
        self.frames[0]['bits'].append(r_list[6])

    def add_one_multi_layer_frame(self, ts, did, r_list):
        assert(did<self.MAX_D_LAYER)
        self.frames[did]['timestamp'].append(ts)
        self.frames[did]['frame_type'].append(r_list[0])
        self.frames[did]['target_qp'].append(r_list[1])
        self.frames[did]['average_qp'].append(r_list[2])

        self.frames[did]['max_qp'].append(r_list[3])
        self.frames[did]['min_qp'].append(r_list[4])
        self.frames[did]['tid'].append(r_list[5])
        self.frames[did]['bits'].append(r_list[6])

        if did>0:
            self.multi_layer_flag = True

    def add_one_skipped_frame(self, ts, r):
        self.skip_list.append(len(self.frames[0]['timestamp']))
        for did in range(self.MAX_D_LAYER):
            self.frames[did]['timestamp'].append(ts)
            self.frames[did]['frame_type'].append(0)
            self.frames[did]['average_qp'].append(0)
            self.frames[did]['bits'].append(0)
            self.frames[did]['min_qp'].append(0)
            self.frames[did]['max_qp'].append(0)

    def get_last_frame_ts(self):
        if sum([len(self.frames[idx]['timestamp']) for idx in range(self.MAX_D_LAYER)]) > 0:
            last_frame_time = [max(self.frames[idx]['timestamp'] for idx in range(self.MAX_D_LAYER))]
            last_frame_time = max(last_frame_time)
        else:
            last_frame_time = 0
        return max(last_frame_time)

    def get_settings(self, time, r):
        cur_settings = {}
        RateControlUtil.settings_log(time, r, cur_settings)
        if self.usage_type == 0:
            cur_settings['timewindow'] = 5000  # ms
            cur_settings['fluctuation_range'] = 0.1
        elif self.usage_type == 1:
            cur_settings['timewindow'] = 10000  # ms
            cur_settings['fluctuation_range'] = 0.3

        cur_settings['target_bit_rate_upper'] = int(cur_settings['target_bit_rate'] * (1+cur_settings['fluctuation_range']) + 0.5)

        self.settings.append(cur_settings)


    def read_logs(self, files):
        self.name = files
        current_file = open(files, 'rU')
        lines = current_file.readlines()
        for line in lines:
            r = self.basic_setting_match_re1.search(line)
            if r is not None:
                self.usage_type = int(r.groups()[0])
                continue

            r = self.setting_match_re.search(line)
            if r is not None:
                setting_time = 0
                if len(self.frames[0]['timestamp']) > 0:
                    setting_time = self.frames[-1].ts
                self.get_settings(setting_time, r)
                continue

            r = self.rc_log_match_re.search(line)
            if r is not None:
                self.add_one_frame(self.check_ts(r.group(1)), [int( r.group(i)) for i in range(2,9)] )
                continue

            r = self.rc_m_log_match_re.search(line)
            if r is not None:
                self.add_one_multi_layer_frame(self.check_ts(r.group(2)), int(r.group(1)), [int( r.group(i)) for i in range(3,10)])
                continue

            r = self.rc_skip_frame_match_re.search(line)
            if r is not None:
                self.add_one_skipped_frame(self.check_ts(r.group(1)), r)
                continue

            r = self.setoption_br_match.search(line)
            if r is not None:
                setting_time = self.get_last_frame_ts()
                RateControlUtil.option_br_update(self.settings, setting_time, int(r.group(1)))
                continue

            r = self.setoption_maxbr_match.search(line)
            if r is not None:
                setting_time = self.get_last_frame_ts()
                RateControlUtil.option_max_br_update(self.settings, setting_time, int(r.group(1)))
                continue

        current_file.close()

    def get_cur_rate(self, bits, time_period):
        return (bits * 1.0 / time_period) *1000

    def generate_sectioned_rate(self, frame_list, start, end, timewindow):
        local_section_time = []
        local_section_rates = []
        frame_timestamp_list = frame_list['timestamp']

        start_idx = timewindow/1000
        window_start = 0
        for idx, ts in enumerate(frame_timestamp_list):
            if start <= ts <= end and ts >= timewindow and ts >= 1000*start_idx:
                #find the window start idx
                for last_idx in range(idx-1, 0, -1):
                    if ts - frame_timestamp_list[last_idx] > timewindow:
                        window_start = last_idx
                        break
                cur_rate = self.get_cur_rate(numpy.sum(frame_list['bits'][window_start:idx]),
                                             ts - frame_timestamp_list[window_start])
                local_section_time.append(ts)
                local_section_rates.append(cur_rate)
                start_idx += 1
        return (local_section_time, local_section_rates)

    def check_overflow(self, rate_list, criterion_rate):
        exceeded_times = 0
        len2 = len(self.section_rates[1])
        for idx, item in enumerate(rate_list):
            if item > criterion_rate and idx < len2 and self.section_rates[1][idx] > criterion_rate:
                exceeded_times += 1
            if item > criterion_rate and idx > 0 and self.section_rates[1][idx-1] > criterion_rate:
                exceeded_times += 1
        return exceeded_times

    def get_aver_line(self, line0, line1):
        aver = []
        aver.append(line0[0])
        for rate1, rate2 in zip(line0[1:], line1):
            aver.append((rate1+rate2)/2)
        return aver

    def update_overall(self, start, end, upper, max):
        self.overall_upper.append(upper)
        if max != INT_MAX:
            self.overall_max.append(max)

        started = False
        start_idx = 0
        end_idx = 0

        for idx, item in enumerate(self.frames['timestamp']):
                if item >= start and item <= end:
                    if started == False:
                        start_idx = idx
                        started = True
                        start_time = self.frames['timestamp'][idx]
                    else:
                        end_idx = idx

        self.overall_time.append((self.frames['timestamp'][start_idx] + self.frames['timestamp'][end_idx])/2)
        self.overall_rates.append(self.get_cur_rate(numpy.sum(self.frames['bits'][start_idx:end_idx]),
                                               (self.frames['timestamp'][end_idx]-self.frames['timestamp'][start_idx])))

    def check_different_settings(self):
        isChecked = False
        overall_max_exceed_times_ratio = 0
        overall_max_burst_ratio = 0

        period_exceed = 0

        for idx, item in enumerate(self.settings):
            start = self.settings[idx]['ts']
            if idx+1 == len(self.settings):
                end = self.frames[idx]['timestamp'][-1]
            else:
                end = self.settings[idx+1]['ts']
            current_target_rate_upper = self.settings[idx]['target_bit_rate_upper']
            current_max_rate = self.settings[idx]['max_bit_rate']
            current_target = self.settings[idx]['target_bit_rate']
            current_tw = self.settings[idx]['timewindow']

            exceed_max_times, max_exceed_times_ratio, max_burst_ratio, average_burst_ratio, period_exceed_flag \
                = self.check_bitrate_overflow(self.frames[idx], current_target, current_target_rate_upper, current_max_rate, current_tw, start, end)

            if max_exceed_times_ratio == -1:
                continue

            overall_max_exceed_times_ratio = max(max_exceed_times_ratio, overall_max_exceed_times_ratio)
            overall_max_burst_ratio = max(max_burst_ratio, overall_max_burst_ratio)
            period_exceed += 1 if period_exceed_flag else 0

        if isChecked:
            return exceed_max_times, overall_max_exceed_times_ratio, -1, overall_max_burst_ratio, -1, (period_exceed*100/len(self.settings))
        else:
            return -1,-1,-1 ,-1,-1,-1

    def check_one_setting(self, target_br, max_br):
        assert(len(self.settings) == 1)
        end = self.get_last_frame_ts()
        start = self.settings[0]['ts']

        period_exceed = 0

        current_target_rate_upper = self.settings[0]['target_bit_rate_upper']
        current_max_rate = self.settings[0]['max_bit_rate']
        current_target = self.settings[0]['target_bit_rate']
        current_tw = self.settings[0]['timewindow']

        assert(target_br*1000 == current_target)
        assert( int(max_br*1000) == current_max_rate)

        max_exceed_times, max_exceed_times_ratio, max_burst_ratio, average_burst_ratio, period_exceed_flag \
            = self.check_bitrate_overflow(self.frames[0], current_target, current_target_rate_upper, current_max_rate, current_tw, start, end)

        max_exceed_times, max_br_burst_ratio = self.check_max_br_overflow(self.frames[0], current_max_rate, start, end)

        period_exceed += 1 if period_exceed_flag else 0

        #self.plot_graph(current_target, current_target_rate_upper, current_max_rate)
        return max_exceed_times, max_exceed_times_ratio, max_br_burst_ratio, max_burst_ratio, average_burst_ratio, \
               (period_exceed if max_exceed_times_ratio!= -1 else -1)


    def check_one_setting_multi_layer(self, did, target_br, max_br):
        end = self.get_last_frame_ts()
        start = self.settings[0]['ts']
        current_target = target_br*1000
        current_target_rate_upper = int(current_target*1.1)
        current_max_rate = max_br*1000
        current_tw = 5000
        period_exceed = 0

        max_exceed_times_ratio, max_burst_ratio, average_burst_ratio, period_exceed_flag \
            = self.check_bitrate_overflow(self.frames[did], current_target, current_target_rate_upper, current_max_rate, current_tw, start, end)
        max_exceed_times, max_br_burst_ratio = self.check_max_br_overflow(self.frames[did], current_max_rate, start, end)

        period_exceed += 1 if period_exceed_flag else 0

        return max_exceed_times, max_exceed_times_ratio, max_br_burst_ratio, max_burst_ratio, average_burst_ratio, \
               (period_exceed if max_exceed_times_ratio!= -1 else -1)

    def check_bitrate_overflow(self, frame_list, current_target, current_target_upper, current_max, current_tw,
                               start, end):
        if end<current_tw:
            sys.stdout.write("Sequence Length(%d) is not enough for analysis(%d)\n"
                                 %(end, current_tw))
            return -1,-1,-1,-1, False

        if current_max > 0:
            current_target_upper = min(current_max, current_target_upper)
        sys.stdout.write("[Current Setting]Start=%d, End=%d, Tar=%d, TarUp=%d, Max=%d\n"
                             %(start, end, current_target, current_target_upper, current_max))

        time_list, rate_list = self.generate_sectioned_rate(frame_list, start, end, current_tw)

        # check max-br
        exceed_max_times = len([ item for item in rate_list if item > current_max ])
        if exceed_max_times > 0:
            sys.stdout.write("[Checking Failed!] Exceed Exceed Max Times=%d\n"
                         %(exceed_max_times))
        max_exceed_times_ratio = exceed_max_times*100 / len(rate_list)

        # check target_br
        period_average = numpy.average(rate_list)

        # check target burst: max
        max_burst_ratio = (numpy.max(rate_list) - current_target)*100/current_target

        # check target burst: average
        average_burst_ratio = numpy.average([ (item-current_target)*100/current_target for item in rate_list if item > current_target ])

        self.section_time.extend(time_list)
        self.section_rates.extend(rate_list)
        self.plot_graph(frame_list, current_target, current_target_upper, current_max)

        return exceed_max_times, max_exceed_times_ratio, max_burst_ratio, average_burst_ratio, \
               (period_average > current_max or period_average > current_target_upper)


    def check_max_br_overflow(self, frame_list, curret_max, start, end):
        if end<1000:
            sys.stdout.write("Sequence Length(%d) is not enough for analyze max-br\n"
                                 %(end))

        frame_timestamp_list = frame_list['timestamp']
        exceed_max_times = 0
        start_idx = 1
        window_start = 0
        max_burst_ratio = 0
        for idx, ts in enumerate(frame_timestamp_list):
            if start <= ts <= end and ts >= 1000*start_idx:
                #find the window start idx
                for last_idx in range(idx-1, 0, -1):
                    if ts - frame_timestamp_list[last_idx] > 1000:
                        window_start = last_idx
                        break
                cur_rate = self.get_cur_rate(numpy.sum(frame_list['bits'][window_start:idx]),
                                             ts - frame_timestamp_list[window_start])
                if cur_rate > curret_max:
                    exceed_max_times += 1
                    max_burst_ratio = max(max_burst_ratio, (cur_rate-curret_max)*100/curret_max)
                    if DEBUG:
                        sys.stdout.write("max-br exceeded at ts=%d, rate=%d, calculation time since %d\n"
                                 %(ts, cur_rate, frame_timestamp_list[window_start]))
                        print(frame_list['bits'][window_start:idx])
                start_idx += 1
        return exceed_max_times, max_burst_ratio


    def check_frame_skip(self, rate_list):
        skip_percentage = rate_list.count(0)*100 / len(rate_list)

        successive_0 = 0
        max_successive = 0
        for idx, item in enumerate(rate_list):
            if item == 0:
                successive_0 += 1
            else:
                if max_successive < successive_0:
                    max_successive = successive_0
                successive_0 = 0

        sys.stdout.write("[Skip Info] (%s) skip_frames=%d, skip_percentaged(over100)=%f, longest successive skip = %d \n"
                         %(self.name, rate_list.count(0), skip_percentage, max_successive))

        return skip_percentage, max_successive

    def plot_graph(self, frame_list, current_target, current_target_uppper, current_max_rate):
        fig, axes = plt.subplots(3, 1, sharex=True)

        plt.xlabel('timestamp')
        axes[0].plot(frame_list['timestamp'], frame_list['bits'], label='frame_bits')
        #axes[0].legend(bbox_to_anchor=(0.3, 1.00, 1., .08))

        axes[1].plot(self.section_time, self.section_rates, 'o-', label='section_rates')
        sys.stdout.write("Line: x=%s; y=%s\n" %(self.section_time, self.section_rates))

        axes[1].axhline(y=current_target, color='g',
                                            linestyle='-', linewidth=1, label='target_bit_rate')
        axes[1].axhline(y=current_target_uppper, color='y',
                                            linestyle='-', linewidth=1, label='target_bit_rate_upper')
        if (current_max_rate != 0):
            axes[1].axhline(y=current_max_rate, color='r',
                                            linestyle='-', linewidth=1, label='max_bit_rate')
        #axes[1].legend(bbox_to_anchor=(0.3, 1.00, 1., .08))

        axes[2].plot(frame_list['timestamp'], frame_list['min_qp'], 'b+', label='min_qp')
        axes[2].plot(frame_list['timestamp'], frame_list['max_qp'], 'r+', label='max_qp')
        axes[2].plot(frame_list['timestamp'], frame_list['average_qp'], 'go', label='average_qp')
        #axes[2].legend(bbox_to_anchor=(0.3, 1.00, 1., .08))

        plt.savefig('Results_Rates_%s.png' %self.name.split(os.sep)[-1])
        plt.show()


    def get_skip_list(self):
        return self.skip_list

    def calculate_avergae_bit_rate(self, frame_list):
        total_bits = numpy.sum(frame_list['bits'])
        if total_bits == 0:
            return 0
        average_bit_rate = (total_bits*1.0 / (frame_list['timestamp'][-1] - frame_list['timestamp'][0]))*1000
        return average_bit_rate

    def get_single_layer_average_bit_rate(self):
        assert(self.multi_layer_flag == False)
        if (len(self.settings) != 1):
            return -1
        self.average_bit_rate = self.calculate_avergae_bit_rate(self.frames[0])
        return self.average_bit_rate


    def get_average_bit_rate(self):
        self.average_bit_rate = []
        for did in range(self.MAX_D_LAYER):
            self.average_bit_rate.append(self.calculate_avergae_bit_rate(self.frames[did]))
        return self.average_bit_rate

    def get_skip_status(self):
        if self.multi_layer_flag:
            max_skip_ratio, max_skip_sucessive = -1, -1
            for did in range(self.MAX_D_LAYER):
                if sum(self.frames[did]['bits'])>0:
                    skip_ratio, skip_sucessive = self.check_frame_skip(self.frames[did]['bits'])
                    max_skip_ratio, max_skip_sucessive = max(skip_ratio, max_skip_ratio), max(skip_sucessive, max_skip_sucessive)
            return max_skip_ratio, max_skip_sucessive
        else:
            return self.check_frame_skip(self.frames[0]['bits'])

    def get_max_qp(self):
        return max(self.frames[0]['max_qp'])


def generate_yuv(bsname, width, height, skip_list):
    rec_yuv = bsname+'_dec.yuv'
    CodecUtil.decode(bsname, rec_yuv)

    copy_yuv = bsname+'_dec_copy.yuv'
    print(skip_list)
    actual_skip_list = []

    for i in skip_list:
        if i == 0:
            sys.stdout.write("Incorrect Skip Idx = 0!\n")
            return None
        copy_one_frame(rec_yuv, copy_yuv, width, height, i-1)
        actual_skip_list.append(i-1)
        os.rename(copy_yuv, rec_yuv)
    # end of processing yuv
    print(actual_skip_list)
    return rec_yuv




def batch_encoder_test(enc_path, usage_type, bit_rate_list, common_fps, multi_layer_flag=False):
    current_path = os.getcwd()
    os.chdir(enc_path)
    for f in glob.glob(enc_path + os.sep + '*.log'):
        os.remove(f)
    for f in glob.glob(enc_path + os.sep + '*.264'):
        os.remove(f)

    fout = open('Results.csv', 'w')
    fout.write('bs_name, rc_mode, frame_skip, target_br, average_br, average_br_ratio, max_qp, psnr_y, '
               'max_burst_ratio, avg_burst_ratio, max_exceed_times, max_exceed_times_ratio, max_br_burst_ratio, period_exceed_ratio, skip_ratio, skip_successive\n')

    if usage_type == 0:
        seq_path = CAMERA_SEQ_PATH
    elif usage_type == 1:
        seq_path = SCREEN_SEQ_PATH

    for frame_skip_iter in frame_skip_list:
        for rc_mode_iter in RC_MODE_LIST:
            for f in glob.glob(seq_path + os.sep + '*.yuv'):
                r = resolution_re.search(f)
                width = int(r.group(1))
                height = int(r.group(2))
                framerate = int(r.group(3))

                max_item = 0
                cur_bit_rate_list = []
                for item in bit_rate_list:
                    if cur_bit_rate_list == [] or ( (width*height/256) >= item and item > max_item ):
                        cur_bit_rate_list = bit_rate_list[item]
                        max_item = item

                for bit_rate_item in cur_bit_rate_list:
                    if multi_layer_flag is False:
                        target_br = int(bit_rate_item*framerate/common_fps)
                        max_br = int(target_br * float(MAX_BR_RATIO))

                        # process each file
                        bs_name, log_name = CodecUtil.call_encoder(f, usage_type,
                                    width, height, framerate,
                                    target_br, max_br, rc_mode_iter, frame_skip_iter)

                        #encoded
                        current_log = cCurrentLog()
                        current_log.read_logs(log_name)

                        max_exceed_times, max_exceed_times_ratio, max_br_burst_ratio, max_burst_ratio, avg_burst_ratio, period_exceed_ratio = current_log.check_one_setting(target_br, max_br)
                        skip_ratio, skip_successive = current_log.get_skip_status()
                        skip_list = current_log.get_skip_list()
                        if frame_skip_iter == 0 and skip_list!=[]:
                            sys.stdout.write("Error! Frameskip(%d) not allowed but there is skipped: %s\n"
                                             %(frame_skip_iter, str(skip_list)))
                            return
                        elif skip_list != [] and skip_list[0] == 0:
                            sys.stdout.write("Incorrect Skip Idx = 0!\n")
                            return

                        average_bit_rate = current_log.get_single_layer_average_bit_rate()
                        if average_bit_rate <= 0:
                            continue

                        rec_yuv = generate_yuv(bs_name, width, height, skip_list)
                        bitrate, psnr_y, psnr_u, psnr_v = calculate_psnr(width, height, f, rec_yuv,
                                             'Results_PSNR', bs_name, framerate)

                        fout.write('%s, %d, %d, %d, %d, %f, %d, %f, %f, %f, %d, %f, %d, %f, %f, %d\n'
                                   %(bs_name, rc_mode_iter, frame_skip_iter, target_br,
                                     average_bit_rate, average_bit_rate*100/(target_br*1000), current_log.get_max_qp(),
                                     psnr_y, max_burst_ratio, avg_burst_ratio, max_exceed_times, max_exceed_times_ratio, max_br_burst_ratio, period_exceed_ratio, skip_ratio, skip_successive))

                        os.remove(rec_yuv)
                    else:
                        target_br = [ int(item*framerate/common_fps) for item in bit_rate_item ]
                        max_br = [ int(item * float(MAX_BR_RATIO)) for item in target_br ]

                        bs_name, log_name = CodecUtil.call_multilayer_encoder(f, usage_type,
                                    width, height, framerate,
                                    target_br, max_br, rc_mode_iter, frame_skip_iter)

                        #encoded
                        current_log = cCurrentLog()
                        current_log.read_logs(log_name)
                        average_bit_rate = current_log.get_average_bit_rate()

                        for did in range(4):
                            if average_bit_rate[did] <= 0:
                                continue

                            max_exceed_times, max_exceed_times_ratio, max_burst_ratio, avg_burst_ratio, period_exceed_ratio \
                                = current_log.check_one_setting_multi_layer(did, target_br[did], max_br[did])

                            skip_ratio, skip_successive = current_log.get_skip_status()
                            fout.write('%s_layer%d, %d, %d, %d, %d, %f, %f, %f, %f, %d, %f, %f, %f, %d\n'
                                       %(bs_name, did, rc_mode_iter, frame_skip_iter, target_br[did],
                                         average_bit_rate[did], average_bit_rate[did]*100/(target_br[did]*1000),
                                         0, max_burst_ratio, avg_burst_ratio, max_exceed_times, max_exceed_times_ratio, period_exceed_ratio, skip_ratio, skip_successive))



    fout.close()
    os.chdir(current_path)


if __name__ == '__main__':
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-enc", nargs='?', default=None, help="encoder path")
    argParser.add_argument("-camera_seq_path", nargs='?', default=None, help="camera_seq_path")
    argParser.add_argument("-screen_seq_path", nargs='?', default=None, help="screen_seq_path")
    argParser.add_argument("-rc_mode", nargs='?', default=None, help="screen_seq_path")
    argParser.add_argument("-max_range", nargs='?', default=None, help="max_range (float, for exmaple, 1.5)")
    argParser.add_argument("-time_window_camera", nargs='?', default=None, help="time_window (milliseconds, for exmaple, 2000 means 2 seconds)")

    argParser.add_argument("-multi_layer_encoding", nargs='?', default=None, help="multi_layer_encoding")

    args = argParser.parse_args()

    if args.camera_seq_path is not None:
        CAMERA_SEQ_PATH = args.camera_seq_path

    if args.screen_seq_path is not None:
        SCREEN_SEQ_PATH = args.screen_seq_path

    if args.rc_mode:
        RC_MODE_LIST = [args.rc_mode, ]

    if args.max_range and args.max_range>1:
        MAX_BR_RATIO = args.max_range

    if args.time_window_camera and args.time_window_camera>1000:
        TIME_WINDOW = args.time_window_camera

    resolution_re = re.compile(r'(\d+)x(\d+)_(\d+)')

    if args.multi_layer_encoding is None:
        camera_bit_rate_list = { 3600: [900, 1200, 1400, 1600], #1280x720
                          1800: [400, 600, 800, 1000], #960x540
                          900: [350, 400, 450, 500, 550, 600], #640x480~640x512
                          500: [300, 330, 360, 390],
                          225: [160,],#[160, 200, 250, 360],  #320x180~320x192~320x240
                          80: [80, 100, 140, 160],   #160x90~160x128
                        }
        camera_typical_bit_rate_list = { 3600: [1200, 1400, ], #1280x720
                          1800: [800, 1000], #960x540
                          900: [500, 600], #640x360~640x512
                          500: [400, 600],
                          225: [200, 400],  #320x180~320x192~320x240
                          80: [120, 140],   #160x90~160x128; 160x90@15_min=64 ==> 160x90@30_min=128
                        }
        screen_bit_rate_list = { 8100: [1500, 2000, 2500, 3000], #1920x1080
                          1200: [800, 1200, 1600, 2000], #
                        }

        batch_encoder_test(args.enc, 0, camera_typical_bit_rate_list, 30)
        #batch_encoder_test(args.enc, 1, camera_bit_rate_list, 10, args.rc_mode)
    else:
        camera_typical_bit_rate_list = { 3600: [[128, 328, 573, 964], [128, 328, 573, 1524], ], #1280x720
                          1800: [[128, 328, 573, 499], [128, 328, 573, 679]], #960x540
                          900: [[128, 328, 373], [128, 328, 573]], #640x360~640x512
                          500: [[100, 200, 311], [150, 328, 351]],
                          225: [[128, 178], [128, 328]],  #320x180~320x192~320x240
                          80: [[128,], [200, ]],   #160x90~160x128; 160x90@15_min=64 ==> 160x90@30_min=128
                        }

        batch_encoder_test(args.enc, 0, camera_typical_bit_rate_list, 30, True)







