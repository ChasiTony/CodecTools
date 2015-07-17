import os
import sys
import subprocess
import re
import __init__

DEBUG=1

def decode(bs, out_yuv):
    cmdline = str('%s %s %s'
                % ('./h264dec', bs, out_yuv))
    p = subprocess.Popen(cmdline, stderr=subprocess.PIPE, shell=True)
    print(p.communicate()[1])

def call_encoder_rc(input_name, usagetype, width, height, frame_rate, target_br, max_br, rc_mode, frame_skip=1):
    bs_name  = input_name.split(os.sep)[-1] + '_br' + str(target_br) + '.264'
    log_name = input_name.split(os.sep)[-1] + '_br' + str(target_br) + '.log'
    if '.yuv' not in input_name:
        input_name += '.yuv'

    rc_mode = int(rc_mode)
    cmdline = '%s -org %s -utype %d -bf %s -sw %d -sh %d -frin %f -numl 1 -numtl 2 -rc %d -fs %d -tarb %d -maxbrTotal %d -trace 255 ' \
              '-dw 0 %d -dh 0 %d -frout 0 %f -ltarb 0 %d -lmaxb 0 %d ' \
              '1> %s 2> %s' \
              % ("./h264enc", input_name, usagetype, bs_name,
                 width, height, frame_rate, rc_mode, frame_skip, target_br, max_br,
                 width, height, frame_rate, target_br, max_br,
                 log_name, log_name)
    if DEBUG:
        sys.stdout.write(cmdline+'\n')
    p = subprocess.Popen(cmdline, stderr=subprocess.PIPE, shell=True)
    sys.stdout.write(p.communicate()[1])
    return bs_name, log_name

def call_encoder_qp(input_name, usage_type, width, height, qp, additional_cmd=''):
    bs_name  = input_name.split(os.sep)[-1] + '_br' + str(qp) + '.264'
    log_name = input_name.split(os.sep)[-1] + '_br' + str(qp) + '.log'

    if os.path.isfile(bs_name):
        os.remove(bs_name)
    if os.path.isfile(log_name):
        os.remove(log_name)
    cmdline = str('./h264enc ./welsenc.cfg -utype %d -numl 1 -lconfig 0 layer2.cfg -frms -1 -lqp 0 %d -rc -1 -trace 7 '
                  '-org %s -bf %s -sw %d -sh %d -dw 0 %d -dh 0 %d %s '
                  '>> %s'
            % (usage_type, qp, input_name, bs_name, width, height,  width, height, additional_cmd,
                   log_name))
    if DEBUG:
        sys.stdout.write(cmdline+'\n')
    p = subprocess.Popen(cmdline, stderr=subprocess.PIPE, shell=True)
    p.communicate()
    return bs_name, log_name


def call_multilayer_encoder(input_name, usagetype, width, height, frame_rate, target_br_list, max_br_list, rc_mode, frame_skip=1):
    layer_num = __init__.get_did_from_resolution(width, height) + 1

    total_target_br = sum(target_br_list[0:layer_num])
    total_max_br = sum(max_br_list[0:layer_num])

    bs_name  = input_name.split(os.sep)[-1] + '_br' + str(total_target_br) + '.264'
    log_name = input_name.split(os.sep)[-1] + '_br' + str(total_target_br) + '.log'
    if '.yuv' not in input_name:
        input_name += '.yuv'

    cmdline = '%s -org %s -utype %d -bf %s -sw %d -sh %d -frin %f -numtl 2 -rc %s -fs %d -trace 255 ' \
              % ("./h264enc", input_name, usagetype, bs_name,
                 width, height, frame_rate, rc_mode, frame_skip)

    cmdline += ' -numl %d -tarb %d -maxbrTotal %d ' %(layer_num, total_target_br, total_max_br)

    for i in range(layer_num):
        cmdline += ' -dw %d %d -dh %d %d -frout %d %f -ltarb %d %d -lmaxb %d %d '\
                   %(i, width/(2**(layer_num-1-i)),
                     i, height/(2**(layer_num-1-i)),
                     i, frame_rate,
                     i, target_br_list[i],
                     i, max_br_list[i])

    cmdline += '1> %s 2> %s' \
              % (log_name, log_name)
    if DEBUG:
        sys.stdout.write(cmdline+'\n')
    p = subprocess.Popen(cmdline, stderr=subprocess.PIPE, shell=True)
    sys.stdout.write(p.communicate()[1])
    return bs_name, log_name




def encoder_log_file(log_file):
    log_file = open(log_file,'r')
    enc_result_line = log_file.read()
    log_file.close()
    print(enc_result_line)

    fps = 0
    match_re_fps = re.compile(r'FPS:\t\t(\d+.\d+) fps')
    r = match_re_fps.search(enc_result_line)
    if r is not None:
        fps = float(r.groups()[0])

    if fps==0:
        print("error!\n")
        return -1
    return fps




def calculate_psnr(width, height, original, rec, output_name=None, bs_name=None, frame_rate=None):
    psnr_path = "/Users/sijchen/WorkingCodes/Tools"

    if bs_name and frame_rate:
        cmdline = str('%sPSNRStaticd %d %d %s %s 0 0 %s %d Summary -r '
                    % (psnr_path+ os.sep, width, height, original, rec, bs_name, frame_rate))
    else:
        cmdline = str('%sPSNRStaticd %d %d %s %s.yuv Summary -r '
                    % (psnr_path+ os.sep, width, height, original, rec))
    if output_name:
        cmdline += ' 1> %s.log' %(output_name)

    print(cmdline)
    p = subprocess.Popen(cmdline, stderr=subprocess.PIPE, shell=True)
    result_line = p.communicate()[1]

    match_re_psnr = re.compile(r'Summary,bitrate \(kbps\)\:,(\d+.\d+),total PSNR:,(\d+.\d+),(\d+.\d+),(\d+.\d+)')
    r = match_re_psnr.search(result_line)

    if r is not None:
        return float(r.group(1)), float(r.group(2)), float(r.group(3)),float(r.group(4))
        # return bit_rate, psnr_y, psnr_u, psnr_v
    else:
        return 0,0,0,0


class cBatchPsnr(object):
    def RateControlUtil(self, filename):
        self.original1_match_re= re.compile(r'Info: Log = (.*).txt; Original = (.*)(\d+)x(\d+)(.*).yuv; BsName = (.*).264;')
        self.original2_match_re= re.compile(r'Info: Log = (.*).txt; Original = (.*).yuv; BsName = (.*).264; Width = (\d+); Height = (\d+);')

        self.lines = []
        current_file = open(filename, 'rU')
        lines = current_file.readlines()
        for line in lines:
            r = self.original1_match_re.search(line)
            if r is not None:
                self.add_original1(r)
                continue

            r = self.original2_match_re.search(line)
            if r is not None:
                self.add_original2(r)
                continue
        current_file.close()

    def add_original1(self, r):
        log_name = r.groups()[0]
        file_name1 = r.groups()[1]
        width      = int(r.groups()[2])
        height     = int(r.groups()[3])
        file_name2 = r.groups()[4]
        bs_name = r.groups()[5]
        original_name = file_name1+str(width)+'x'+str(height)+file_name2+'.yuv'
        self.lines.append([log_name+'.txt', original_name, bs_name+'.264', width, height])

    def add_original2(self, r):
        log_name = r.groups()[0]
        file_name = r.groups()[1]
        bs_name = r.groups()[2]
        width      = int(r.groups()[3])
        height     = int(r.groups()[4])
        self.lines.append([log_name+'.txt', file_name+'.yuv', bs_name+'.264', width, height])

    def get_lines(self):
        return self.lines




def get_resolution_from_name(f):
    resolution_re = re.compile(r'(\d+)x(\d+)_(\d+)')
    r = resolution_re.search(f)
    if r is not None:
        width = int(r.group(1))
        height = int(r.group(2))
        framerate = int(r.group(3))
        return width, height, framerate

    resolution_re2 = re.compile(r'(\d+)x(\d+)')
    r = resolution_re2.search(f)
    if r is not None:
        width = int(r.group(1))
        height = int(r.group(2))
        return width, height, 30

    return 0, 0, 0