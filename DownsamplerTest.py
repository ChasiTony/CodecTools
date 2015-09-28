import os, sys, subprocess
import glob
import argparse
import __init__, CodecUtil
from BDRate import calculate_from_two_dicts, OneTestPoint, write_testpoint_to_csv
import re


JSVM_DOWNSAMPLER = "/Users/guangwwa/WorkSpace/Tools/DownConvert/bin/DownConvert"
#Usage: DownConvertStatic.exe <win> <hin> <in> <wout> <hout> <out> [<method> [<t>
# [<skip> [<frms>]]]] [[-crop <args>] [-phase <args>] [-resample_mode <arg>]]

DOWNSAMPLER = "/Users/guangwwa/WorkSpace/Tools/downsampler/bin/downsampler"
#./downsapmpler infilename.yuv src_width src_height outfilename1.yuv outfilename2.yuv dst_width dst_height

H264ENCODER = '/Users/guangwwa/WorkSpace/openh264/h264enc'
#./h264 welsenc.cfg [option]


def jsvm_downsampler(win, hin, yuv_in, wout, hout, yuv_out):
    #TODO: fill in correct command line
    cmdline = str('%s %s %s %s %s %s %s'
                % (JSVM_DOWNSAMPLER, win, hin, yuv_in, wout, hout, yuv_out))
    p = subprocess.Popen(cmdline, stderr=subprocess.PIPE, shell=True)
    print(p.communicate()[1])
    return yuv_out

def test_downsampler(yuv_in, win, hin, yuv_out_general, yuv_out_specific, wout, hout):
    #TODO: fill in correct command line
    cmdline = str('%s %s %s %s %s %s %s %s'
                % (DOWNSAMPLER, yuv_in, win, hin, yuv_out_general, yuv_out_specific, wout, hout))
    p = subprocess.Popen(cmdline, stderr=subprocess.PIPE, shell=True)
    print(p.communicate()[1])
    return yuv_out_general, yuv_out_specific

def h264enc(infile,outfile,sw,sh):
    h264enc_path = '/Users/guangwwa/WorkSpace/openh264/'
    cfg_file_path = '/Users/guangwwa/WorkSpace/openh264/testbin/'
    
    cmdline = str('%sh264enc welsenc.cfg -org %s -sw %d -sh %d -frms 1000 -frin 30 -bf %s -dw 0 %d -dh 0 %d' %(h264enc_path, infile,sw,sh,outfile,sw,sh))
    p = subprocess.Popen(cmdline, stdout=subprocess.PIPE, shell=True)
    result_line = p.communicate()[0]
    print result_line
    match_re_enc = re.compile(r'Width:\t\t(.*)\nHeight:\t\t(.*)\nFrames:\t\t(.*)\nencode time:\t(.*) sec\nFPS:\t\t(.*) fps\n')
    
    r = match_re_enc.search(result_line)
    if r is not None:
        return r.group(3), r.group(4), r.group(5)
    else:
        return 0,0,0
    

def process_downsampler_compare(yuv_list,downscale):
    f1 = open(__init__.OUT_DATA_PATH + 'psnrCompare1' + '_%d' %downscale + '.csv', 'w')
    f2 = open(__init__.OUT_DATA_PATH + 'psnrCompare2' + '_%d' %downscale + '.csv', 'w')
    f3 = open(__init__.OUT_DATA_PATH + 'psnrCompare3' + '_%d' %downscale + '.csv', 'w')
    f1.write('filename,psnr_y,psnr_u,psnr_v\n')
    f2.write('filename,psnr_y,psnr_u,psnr_v\n')
    f3.write('filename,psnr_y,psnr_u,psnr_v\n')

    for one_yuv in yuv_list:
        width, height, framerate = CodecUtil.get_resolution_from_name(one_yuv)
        width_out = width/downscale
        height_out = height/downscale
        out_yuv_resolution = '%d' %width_out + 'x' + '%d' %height_out

        jsvm_out = __init__.OUT_DATA_PATH + os.path.basename(one_yuv)[0:-4] + '_to_' + out_yuv_resolution + '_downConvert.yuv'
        downsampler1_out = __init__.OUT_DATA_PATH + os.path.basename(one_yuv)[0:-4] + '_to_' + out_yuv_resolution + '_downsampler1.yuv'
        downsampler2_out = __init__.OUT_DATA_PATH + os.path.basename(one_yuv)[0:-4] + '_to_' + out_yuv_resolution + '_downsampler2.yuv'

        jsvm_downsampler(width, height, one_yuv, width_out, height_out, jsvm_out)
        test_downsampler(one_yuv, width, height, downsampler1_out, downsampler2_out, width_out, height_out)

        # psnr ing
        psnr_y1, psnr_u1, psnr_v1 = CodecUtil.calculate_psnr(width_out, height_out, jsvm_out, downsampler1_out)
        f1.write('%s,%s,%s,%s\n' %(os.path.basename(one_yuv), psnr_y1, psnr_u1, psnr_v1))
        psnr_y2, psnr_u2, psnr_v2 = CodecUtil.calculate_psnr(width_out, height_out, jsvm_out, downsampler2_out)
        f2.write('%s,%s,%s,%s\n' %(os.path.basename(one_yuv), psnr_y2, psnr_u2, psnr_v2))
        psnr_y3, psnr_u3, psnr_v3 = CodecUtil.calculate_psnr(width_out, height_out, downsampler1_out, downsampler2_out)
        f3.write('%s,%s,%s,%s\n' %(os.path.basename(one_yuv), psnr_y3, psnr_u3, psnr_v3))
        #TODO: output psnr into a file, csv is the best

    f1.close()
    f2.close()
    f3.close()

def process_compare_enc(yuv_list,downscale):
    f1 = open(__init__.OUT_DATA_PATH + 'encCompare' + '_%d' %downscale + '.csv', 'w' )
    f1.write('filename,width,height,frames,DownConvert_encode_time,DownConvert_fps,downsampler1_encode_time,downsampler1_fps,downsampler2_encode_time,downsampler2_fps\n')
    for one_yuv in yuv_list:
        width, height, framerate = CodecUtil.get_resolution_from_name(one_yuv)
        width_out = width/downscale
        height_out = height/downscale
        out_yuv_resolution = '%d' %width_out + 'x' + '%d' %height_out

        jsvm_out = __init__.OUT_DATA_PATH + os.path.basename(one_yuv)[0:-4] + '_to_' + out_yuv_resolution + '_downConvert.yuv'
        downsampler1_out = __init__.OUT_DATA_PATH + os.path.basename(one_yuv)[0:-4] + '_to_' + out_yuv_resolution + '_downsampler1.yuv'
        downsampler2_out = __init__.OUT_DATA_PATH + os.path.basename(one_yuv)[0:-4] + '_to_' + out_yuv_resolution + '_downsampler2.yuv'

        jsvm_out_264 = jsvm_out[:-4] + '.264'
        downsampler1_out_264 = downsampler1_out[:-4] + '.264'
        downsampler2_out_264 = downsampler2_out[:-4] + '.264'

        # encoder three yuv files
        frames, enc_time, fps = h264enc(jsvm_out,jsvm_out_264,width_out,height_out)
        f1.write('%s,%s,%s,%s,%s,%s,' %(os.path.basename(one_yuv),width_out,height_out,frames,enc_time,fps))
        frames,enc_time, fps = h264enc(downsampler1_out,downsampler1_out_264,width_out,height_out)
        f1.write('%s,%s,' %(enc_time,fps))
        frames,enc_time, fps = h264enc(downsampler2_out,downsampler2_out_264,width_out,height_out)
        f1.write('%s,%s\n' %(enc_time,fps))
    f1.close()

if __name__ == '__main__':
    #set you search path in __init__.py
    default_yuv_path = __init__.TEST_SEQ_PATH

    downscale = 4

    yuv_list = []
    for f in glob.glob(default_yuv_path + '*.yuv'):
        yuv_list.append(f)

    anchor_dict = process_downsampler_compare(yuv_list,downscale)
    process_compare_enc(yuv_list,downscale)


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


















