import os, sys, subprocess
import glob
import argparse
import __init__, CodecUtil
from BDRate import calculate_from_two_dicts, OneTestPoint, write_testpoint_to_csv


JSVM_DOWNSAMPLER = "/Users/sijchen/WorkingCodes/Tools/DownConvertStatic.exe"
#Usage: DownConvertStatic.exe <win> <hin> <in> <wout> <hout> <out> [<method> [<t>
# [<skip> [<frms>]]]] [[-crop <args>] [-phase <args>] [-resample_mode <arg>]]

DOWNSAMPLER = "/Users/sijchen/WorkingCodes/Github/downsampler/bin/downsampler"
#./downsapmpler infilename.yuv src_width src_height out filename.yuv dst_width dst_height


def jsvm_downsampler(one_yuv, width, height):
    #TODO: fill in correct command line
    cmdline = str('%s %s '
                % ('./JSVM_DOWNSAMPLER', one_yuv))
    p = subprocess.Popen(cmdline, stderr=subprocess.PIPE, shell=True)
    print(p.communicate()[1])
    return jsvm_out

def test_downsampler(one_yuv, width, height):
    #TODO: fill in correct command line
    cmdline = str('%s %s '
                % ('./DOWNSAMPLER', one_yuv))
    p = subprocess.Popen(cmdline, stderr=subprocess.PIPE, shell=True)
    print(p.communicate()[1])
    return downsampler1_out, downsampler2_out

def process_downsampler_compare(yuv_list):
    for one_yuv in yuv_list:
        width, height, framerate = CodecUtil.get_resolution_from_name(one_yuv)

        jsvm_out = jsvm_downsampler(one_yuv, width, height)
        downsampler1_out, downsampler2_out = test_downsampler(one_yuv, width, height)

        # psnr ing
        bitrate, psnr_y1, psnr_u1, psnr_v1 = CodecUtil.calculate_psnr(width, height, jsvm_out, downsampler1_out)
        bitrate, psnr_y2, psnr_u2, psnr_v2 = CodecUtil.calculate_psnr(width, height, jsvm_out, downsampler2_out)
        #TODO: output psnr into a file, csv is the best
        

if __name__ == '__main__':
    default_yuv_path = __init__.CAMERA_SEQ_PATH
    yuv_list = []
    for f in glob.glob(default_yuv_path + os.sep + '*.yuv'):
        yuv_list.append(f)

    anchor_dict = process_downsampler_compare(JSVM_DOWNSAMPLER, yuv_list)


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


















