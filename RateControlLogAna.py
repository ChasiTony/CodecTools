#!/usr/bin/env python
import sys
import argparse
import matplotlib.pyplot as plt

import __init__, RateControlUtil
from RateControlTest import cCurrentLog


class cProductionLog(object):
    def __init__(self):
        self.MAX_D_LAYER = 4

        self.rc_skip_frame_match_re = RateControlUtil.RC_DEBUG_SKIPLOG_RE

        self.name = None
        self.multi_layer_flag = False

        self.settings = []
        self.stats = []
        self.idr = []
        self.frame_skipped = []
        self.layer_stats = []

        self.dt_list = []
        self.br_list = []

    def check_ts(self, input):
        cur_ts = int(input)
        if cur_ts == 0 and len(self.frames[0]['timestamp'])>0:
            # ts is not valid
            cur_ts = int(1000/self.settings[-1]['frame_rate']) + self.frames[0]['timestamp'][-1]
        return cur_ts

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
            r = RateControlUtil.SETTING_TYPE_RE.search(line)
            if r is not None:
                cur_dt = RateControlUtil.extract_timestamp(line)
                self.usage_type = int(r.groups()[0])
                continue

            r = RateControlUtil.LAYER_SETTING_RE.search(line)
            if r is not None:
                cur_dt = RateControlUtil.extract_timestamp(line)
                self.get_settings(cur_dt, r)
                continue

            r = RateControlUtil.SETOPTION_BR_RE.search(line)
            if r is not None:
                cur_dt = RateControlUtil.extract_timestamp(line)
                RateControlUtil.option_br_update(self.settings, cur_dt, int(r.group(1)))
                continue

            r = RateControlUtil.SETOPTION_MAXBR_RE.search(line)
            if r is not None:
                cur_dt = RateControlUtil.extract_timestamp(line)
                RateControlUtil.option_max_br_update(self.settings, cur_dt, int(r.group(1)))
                continue

            r = RateControlUtil.ENCODER_STAT_LOG_RE.search(line)
            if r is not None:
                cur_dt = RateControlUtil.extract_timestamp(line)
                ts = self.check_ts(r.group(14))
                encoded_bytes = int(r.group(13))
                self.stats.append((cur_dt, ts, encoded_bytes))

                self.idr.append(int(r.group(12)))
                self.frame_skipped.append(int(r.group(9)))
                continue

            r = RateControlUtil.VIDEO_LAYER_LOG_RE.search(line)
            if r is not None:
                cur_dt = RateControlUtil.extract_timestamp(line)
                did = __init__.get_did_from_resolution(int(r.group(1)),int(r.group(2)))
                br = int(r.group(4))
                if br>0:
                    self.layer_stats.append((cur_dt, did, br))
                continue

        current_file.close()

    def calculate_stats(self, start_dt, end_dt, cur_th):
        for idx in range(len(self.stats)-1):
            dt1, ts1, bytes1 = self.stats[idx]
            dt2, ts2, bytes2 =  self.stats[idx+1]
            if dt1 < start_dt:
                continue
            if dt2 > end_dt:
                return

            time1 = (dt2 - dt1).total_seconds()*1000
            time2 = (ts2 - ts1)
            if abs(time1-time2)>300:
                sys.stdout.write("Warning! TimeDiff found in timestamp and actual time: actual: %d, timestamp:%d\n"
                                 %(time1, time2))

            delta_bytes = bytes2 - bytes1
            if delta_bytes<0:
                continue
            cur_br = (delta_bytes*8 / time1)*1000
            if cur_br > cur_th:
                sys.stdout.write("Warning! Large BR%d at time %s\n"
                                 %(cur_br, dt2))
            self.dt_list.append(dt2)
            self.br_list.append(cur_br)

    def check_stats(self):
        settings2 = self.settings[1:]

        for set1, set2 in zip(self.settings, settings2):
            self.calculate_stats(set1['ts'], set2['ts'],
                                 min(set1['max_bit_rate'], set1['target_bit_rate_upper']) if set1['max_bit_rate']!= 0 else set1['target_bit_rate_upper'])

    def plot_overall_graph(self):
        max_d_layer = max([item['did'] for item in self.settings])
        axes_count = 2 if max_d_layer == 0 else (1+self.MAX_D_LAYER)
        axes_count += 1 if max(self.idr) > 0 else 0
        axes_count += 1 if max(self.frame_skipped) > 0 else 0
        print('draw %d charts\n' %axes_count)
        fig, axes = plt.subplots(axes_count, 1, sharex=True)
        plt.xlabel('time')

        axes[0].plot(self.dt_list, self.br_list, label='actual_bit_rate')

        if max_d_layer>0:
            for layer_idx in range(self.MAX_D_LAYER):
                cur_list = [item for item in self.settings
                            if layer_idx == __init__.get_did_from_resolution(item['width'],item['height'])]
                if cur_list == []:
                    axes[layer_idx+1].plot(self.dt_list, self.br_list, label='actual_bit_rate')
                else:
                    for info in ('max_bit_rate', 'target_bit_rate_upper'):
                        axes[layer_idx+1].plot([item['ts'] for item in cur_list],
                                 [item[info] for item in cur_list],
                                 label=info+'_%d' %layer_idx)

                cur_list = [item for item in self.layer_stats if item[1]==layer_idx]
                if cur_list == []:
                    axes[layer_idx+1].plot(self.dt_list, self.br_list, label='actual_bit_rate')
                else:
                    axes[layer_idx+1].plot([item[0] for item in cur_list],
                                 [item[2] for item in cur_list],
                                 label='br_%d' %layer_idx)

        else:
            cur_list = [item for item in self.settings]
            for info in ('max_bit_rate', 'target_bit_rate_upper', 'target_bit_rate'):
                axes[0].plot([item['ts'] for item in cur_list],
                                 [item[info] for item in cur_list],
                                 label=info)
            axes[1].plot([item['ts'] for item in self.settings],
                     [item['width']+item['height'] for item in self.settings], label='resolution')

        axes_idx = 2 if max_d_layer==0 else (1+self.MAX_D_LAYER)
        if max(self.idr) > 0:
            axes[axes_idx].plot([item[0] for item in self.stats[1:]],
                                  RateControlUtil.get_derive(self.idr),
                                  '-o', label='idr_count')
            axes_idx += 1

        if max(self.frame_skipped) > 0:
            axes[axes_idx].plot([item[0] for item in self.stats[1:]],
                                  RateControlUtil.get_derive(self.frame_skipped),
                                  '-o', label='frame_skipped_count')
        x=[item[0] for item in self.stats[1:]]
        y=RateControlUtil.get_derive(self.frame_skipped)
        for p1,p2 in zip(x,y):
            print("%s,%d\n" %(p1,p2))

        plt.legend()

        plt.savefig('RatesinLog.png')
        plt.show()



if __name__ == '__main__':
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-log", nargs='?', default=None, help="log file")
    argParser.add_argument("-debug", nargs='?', default=False, help="is RC debug trace exist")
    args = argParser.parse_args()

    if args.log is not None:
        if args.debug:
            current_log = cCurrentLog()
            current_log.read_logs(args.log)

            max_exceed_times, max_exceed_times_ratio, max_br_burst_ratio, max_burst_ratio, avg_burst_ratio, period_exceed_ratio = \
                current_log.check_different_settings()
            skip_ratio, skip_successive = current_log.get_skip_status()

            current_log.plot_overall_graph()

        else:
            current_log = cProductionLog()
            current_log.read_logs(args.log)
            current_log.check_stats()
            current_log.plot_overall_graph()



