#!/usr/bin/env python
import os, sys, subprocess
import glob
import argparse
import __init__, config, CodecUtil
from BDRate import calculate_from_two_dicts, OneTestPoint, write_testpoint_to_csv


#JSVM_DOWNSAMPLER = "DownConvert"
#Usage: DownConvertStatic.exe <win> <hin> <in> <wout> <hout> <out> [<method> [<t>
# [<skip> [<frms>]]]] [[-crop <args>] [-phase <args>] [-resample_mode <arg>]]

#DOWNSAMPLER
#./downsapmpler infilename.yuv src_width src_height outfilename1.yuv outfilename2.yuv dst_width dst_height

H264CODEC_PATH = config.DEFAULT_OPENH264

def jsvm_downsampler(win, hin, yuv_in, wout, hout, yuv_out):
    cmdline = str('%s %s %s %s %s %s %s'
                % (JSVM_DOWNSAMPLER+os.sep+'DownConvert', win, hin, yuv_in, wout, hout, yuv_out))
    p = subprocess.Popen(cmdline, stderr=subprocess.PIPE, shell=True)
    print(p.communicate()[1])
    return yuv_out

def test_downsampler(yuv_in, win, hin, yuv_out_general, yuv_out_specific, wout, hout):
    cmdline = str('%s %s %s %s %s %s %s %s'
                % (DOWNSAMPLER+os.sep+'downsampler', yuv_in, win, hin, yuv_out_general, yuv_out_specific, wout, hout))
    p = subprocess.Popen(cmdline, stderr=subprocess.PIPE, shell=True)
    print(p.communicate()[1])
    return yuv_out_general, yuv_out_specific
    

def process_downsampler_compare(yuv_list,downscale):
    out_path = __init__.OUT_DATA_PATH

    f1 = open(out_path + os.sep + 'psnrCompare1' + '_%d' %downscale + '.csv', 'w')
    f2 = open(out_path + os.sep + 'psnrCompare2' + '_%d' %downscale + '.csv', 'w')
    f3 = open(out_path + os.sep + 'psnrCompare3' + '_%d' %downscale + '.csv', 'w')
    f1.write('filename,psnr_y,psnr_u,psnr_v\n')
    f2.write('filename,psnr_y,psnr_u,psnr_v\n')
    f3.write('filename,psnr_y,psnr_u,psnr_v\n')

    for one_yuv in yuv_list:
        width, height, framerate = CodecUtil.get_resolution_from_name(one_yuv)
        width_out = width/downscale
        height_out = height/downscale
        out_yuv_resolution = '%d' %width_out + 'x' + '%d' %height_out

        jsvm_out = out_path + os.sep + os.path.basename(one_yuv)[0:-4] + '_to_' + out_yuv_resolution + '_downConvert.yuv'
        downsampler1_out = out_path + os.sep + os.path.basename(one_yuv)[0:-4] + '_to_' + out_yuv_resolution + '_downsampler1.yuv'
        downsampler2_out = out_path + os.sep + os.path.basename(one_yuv)[0:-4] + '_to_' + out_yuv_resolution + '_downsampler2.yuv'

        jsvm_downsampler(width, height, one_yuv, width_out, height_out, jsvm_out)
        test_downsampler(one_yuv, width, height, downsampler1_out, downsampler2_out, width_out, height_out)

        # psnr ing
        # ??? should the parameter output_name be None?
        frame_num, bitrate, psnr_y1, psnr_u1, psnr_v1 = CodecUtil.PSNRStaticd(width_out, height_out, jsvm_out, downsampler1_out,
				downsampler1_out+'.log')
        f1.write('%s,%f,%f,%f\n' %(os.path.basename(one_yuv), psnr_y1, psnr_u1, psnr_v1))

        frame_num, bitrate, psnr_y2, psnr_u2, psnr_v2 = CodecUtil.PSNRStaticd(width_out, height_out, jsvm_out, downsampler2_out,
				downsampler2_out+'.log')
        f2.write('%s,%f,%f,%f\n' %(os.path.basename(one_yuv), psnr_y2, psnr_u2, psnr_v2))

        frame_num, bitrate, psnr_y3, psnr_u3, psnr_v3 = CodecUtil.PSNRStaticd(width_out, height_out, downsampler1_out, downsampler2_out,
				downsampler1_out+downsampler2_out+'.log')
        f3.write('%s,%f,%f,%f\n' %(os.path.basename(one_yuv), psnr_y3, psnr_u3, psnr_v3))
        #TODO: output psnr into a file, csv is the best

    f1.close()
    f2.close()
    f3.close()


def process_compare_enc(yuv_list,downscale):
    TestPoint_dict = {}
    out_path = __init__.OUT_DATA_PATH

    for one_yuv in yuv_list:
        width, height, frame_rate = CodecUtil.get_resolution_from_name(one_yuv)
        width_out = width/downscale
        height_out = height/downscale
        out_yuv_resolution = '%d' %width_out + 'x' + '%d' %height_out

        jsvm_out = out_path + os.sep + os.path.basename(one_yuv)[0:-4] + '_to_' + out_yuv_resolution + '_downConvert.yuv'
        downsampler1_out = out_path + os.sep + os.path.basename(one_yuv)[0:-4] + '_to_' + out_yuv_resolution + '_downsampler1.yuv'
        downsampler2_out = out_path + os.sep + os.path.basename(one_yuv)[0:-4] + '_to_' + out_yuv_resolution + '_downsampler2.yuv'

        # encoder three yuv files
        qp = 24
        usage_type = 0
        current_path = os.getcwd()
        os.chdir(H264CODEC_PATH)
        for source in (jsvm_out, downsampler1_out, downsampler2_out):
            bs_name, log_name, result_line = CodecUtil.call_encoder_qp(source, usage_type, width_out, height_out, qp)

            rec_yuv = bs_name[0:-4] +'_dec.yuv'
            CodecUtil.decode(bs_name, rec_yuv)

            # encoder information 
            frames, encode_time, fps = CodecUtil.process_encoder_out_info(log_name)

            # psnr ing
            # ??? should the parameter output_name be None?
            frame_num, bitrate, psnr_y, psnr_u, psnr_v = CodecUtil.PSNRStaticd(width, height, one_yuv, rec_yuv,
					rec_yuv+'.log', bs_name, frame_rate)

            file_size = os.path.getsize(bs_name)
            current_test_point = OneTestPoint(width, height, frame_rate, frames, qp, file_size, encode_time, fps, bitrate, psnr_y, psnr_u, psnr_v)

            if not TestPoint_dict.has_key(source):
                TestPoint_dict[source] = {}
            if not TestPoint_dict[source].has_key(qp):
                TestPoint_dict[source][qp] = {}
            TestPoint_dict[source][qp] = current_test_point

        os.chdir(current_path)

    write_testpoint_to_csv(os.getcwd(), __init__.OUT_DATA_PATH, TestPoint_dict, str('encCompare' + '_%d' %downscale) )

if __name__ == '__main__':
    #set you search path in config.py
    argParser = argparse.ArgumentParser()
    argParser.add_argument("-exepath", nargs='?', help="exe path")
    argParser.add_argument("-jsvm", nargs='?', help="jsvm downconvert path")
    argParser.add_argument("-yuvpath", nargs='?', default=None, help="yuv path")
    argParser.add_argument("-usagetype", nargs='?', default=None, help="camera=0 or screen=1")
    argParser.add_argument("-downscale", nargs='?', default=4, type=int, help="downscale")
    argParser.add_argument("-out", nargs='?', default=None, help="set out path")

    # set downscale
    args = argParser.parse_args()
    downscale = args.downscale

    # set test downsampler
    if not os.path.isdir(args.exepath):
        sys.stdout.write('Invalid exepath %s\n' %args.exepath)
    else:
        sys.stdout.write('current exe path is %s\n' %args.exepath)
        DOWNSAMPLER = args.exepath

    # set jsvm downsampler
    if not os.path.isdir(args.jsvm):
        sys.stdout.write('Invalid exepath %s\n' %args.jsvm)
    else:
        sys.stdout.write('current exe path is %s\n' %args.jsvm)
        JSVM_DOWNSAMPLER = args.jsvm

    # set out path
    if args.out is not None:
        if not os.path.isdir(args.out):
            sys.stdout.write('Invalid outpath %s\n' %args.out)
        else:
            sys.stdout.write('current exe path is %s\n' %args.out)
            config.OUT_DATA_PATH = args.out

    yuv_list = []
    if args.yuvpath is not None:
        for f in glob.glob(args.yuvpath + os.sep + '*.yuv'):
            yuv_list.append(f)
    elif args.usagetype is None:
        for f in glob.glob(config.CAMERA_SEQ_PATH + os.sep + '*.yuv'):
            yuv_list.append(f)
        for f in glob.glob(config.SCREEN_SEQ_PATH + os.sep + '*.yuv'):
            yuv_list.append(f)
    elif args.usagetype == 1:
        for f in glob.glob(config.SCREEN_SEQ_PATH + os.sep + '*.yuv'):
            yuv_list.append(f)
    elif args.usagetype == 0:
        for f in glob.glob(config.CAMERA_SEQ_PATH + os.sep + '*.yuv'):
            yuv_list.append(f)
    else:
        for f in glob.glob(config.TMP_FOLDER + os.sep + '*.yuv'):
            yuv_list.append(f)

    if yuv_list == []:
        sys.stdout.write("not input sequences specified!\n")
        exit()

    anchor_dict = process_downsampler_compare(yuv_list,downscale)
    process_compare_enc(yuv_list,downscale)



