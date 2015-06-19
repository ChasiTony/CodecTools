
# RC log util
import re
from dateutil import parser as dt_parser

SETTING_TYPE_RE = re.compile(r'iUsageType = (\d+)')

# [OpenH264] Info:sSpatialLayers[0]: .iVideoWidth= 1920; .iVideoHeight= 1088; .fFrameRate= 12.000000f; .iSpatialBitrate= 2000000; .iMaxSpatialBitrate= 2100000; .sSliceCfg.uiSliceMode= 0; .sSliceCfg.sSliceArgument.iSliceNum= 1; .sSliceCfg.sSliceArgument.uiSliceSizeConstraint= 1500;               uiProfileIdc = 66;uiLevelIdc = 15
LAYER_SETTING_RE = re.compile(r'Info:sSpatialLayers\[(\d+)\]: .iVideoWidth= (\d+); .iVideoHeight= (\d+); .fFrameRate= (\d+.\d+)f; .iSpatialBitrate= (\d+); .iMaxSpatialBitrate= (\d+); .sSliceCfg.uiSliceMode= (\d+); .sSliceCfg.sSliceArgument.iSliceNum= (\d+); .sSliceCfg.sSliceArgument.uiSliceSizeConstraint= (\d+)')

SETOPTION_BR_RE = re.compile(r'CWelsH264SVCEncoder::SetOption\(\):ENCODER_OPTION_BITRATE layerId= (\d+),iSpatialBitrate = (\d+)')
SETOPTION_MAXBR_RE = re.compile(r'CWelsH264SVCEncoder::SetOption\(\):ENCODER_OPTION_MAX_BITRATE layerId= (\d+),iMaxSpatialBitrate = (\d+)')

        # [OpenH264] Debug:[Rc] Frame timestamp =        0, Frame type =2, encoding_qp0, average qp =  30, index =        0, iTid = 0, used =  1013856, bitsperframe =   159091, target =   636363, remaingbits =   417962, skipbuffersize =   954545
        # [OpenH264] Debug:[Rc] Frame timestamp =        0, Frame type =2, encoding_qp0, average qp =  30, max qp =  30, min qp =  30, index =        0,    iTid = 0, used =  1013856,
        #[Rc] Frame timestamp = 0, Frame type = 2, encoding_qp = 30, average qp = 30, max qp = 30, min qp = 30, index = 0, iTid = 0, used = 53824, bitsperframe = 2133, target = 8532, remaingbits = -36760, skipbuffersize = 32000
        # [Rc]Layer 0: Frame timestamp = 0, Frame type = 2, encoding_qp = 28, average qp = 28, max qp = 28, min qp = 28, index = 0, iTid = 0, used = 23824, bitsperframe = 5000, target = 20000, remaingbits = 16176, skipbuffersize = 75000
        # [OpenH264] Debug:[Rc] Frame timestamp =       83, skip one frame
RC_DEBUG_LOG_RE = re.compile(r'\[Rc\] Frame timestamp = (\d+), Frame type = (\d+), encoding_qp = (\d+), average qp = (\d+), '
                                          r'max qp = (\d+), min qp = (\d+), index = \d+, iTid = (\d+), '
                                          r'used = (\d+), bitsperframe = (\d+), target = (\d+), remaingbits = ([-]?\d+), skipbuffersize = (\d+)')
RC_DEBUG_LOG_RE2 = re.compile(r'\[Rc\]Layer (\d+):\sFrame timestamp = (\d+), Frame type = (\d+), encoding_qp = (\d+), average qp = (\d+), '
                                          r'max qp = (\d+), min qp = (\d+), index = \d+, iTid = (\d+), '
                                          r'used = (\d+), bitsperframe = (\d+), target = (\d+), remainingbits = ([-]?\d+), skipbuffersize = (\d+)')
RC_DEBUG_SKIPLOG_RE = re.compile(r'\[Rc\] Frame timestamp = (\d+), skip one frame')
RC_DEBUG_LOG_RE3 = re.compile(r'\[Rc\] bits in buffer = (\d+)')


#b/RateControlTest/logs.txt:64: 2015-05-28T01:00:23.987, INFO, 17803, SQ_WME_LOG: [2] [OpenH264] this = 0x0x60000025a430, Info:EncoderStatistics: 160x90, SpeedInMs: 0.903073, fAverageFrameRate=5821.016113,                LastFrameRate=17.000000, LatestBitRate=132190, LastFrameQP=24, uiInputFrameCount=58443, uiSkippedFrameCount=2539,                uiResolutionChangeTimes=110, uIDRReqNum=457, uIDRSentNum=625, uLTRSentNum=NA, iTotalEncodedBytes=124175               at Ts = 2550714412
ENCODER_STAT_LOG_RE = re.compile(r'EncoderStatistics: (\d+)x(\d+), SpeedInMs: (\d+.\d+), '
                                 r'fAverageFrameRate=(\d+.\d+),\s+LastFrameRate=(\d+.\d+), LatestBitRate=(\d+), LastFrameQP=(\d+), '
                                 r'uiInputFrameCount=(\d+), uiSkippedFrameCount=(\d+),\s+uiResolutionChangeTimes=(\d+), '
                                 r'uIDRReqNum=(\d+), uIDRSentNum=(\d+), uLTRSentNum=NA, iTotalEncodedBytes=(\d+)(?:\s+)?at Ts = (\d+)')

VIDEO_LAYER_LOG_RE = re.compile(r'Video Layer -  w\*h=(\d+)x(\d+) fps=(\d+) br=(\d+)')

# 2014-05-14T22:02:21.066
timestamp_re = re.compile(r'(\d\d\d\d-\d\d-\d\d\w\d\d:\d\d:\d\d\.\d\d\d)')

# return datetime
def extract_timestamp(line):
    # extract timestamp
    match = timestamp_re.search(line)
    if match is None:
        # print 'Error in timestamp format: %s' % line
        return None

    return dt_parser.parse(match.groups()[0])

def settings_log(time, r, cur_settings):
    cur_settings['ts'] = time
    cur_settings['did'] = int(r.group(1))
    cur_settings['width'] = int(r.group(2))
    cur_settings['height'] = int(r.group(3))
    cur_settings['frame_rate'] = float(r.group(4))
    cur_settings['target_bit_rate'] = int(r.group(5))
    cur_settings['max_bit_rate'] = int(r.group(6))
    #cur_settings['slice_mode'], cur_settings['slice_num'], cur_settings['slice_size']  = int(r.groups()[7:10])
    return cur_settings

def option_br_update(cur_list, time, br):
    cur_settings = cur_list[-1].copy()
    cur_settings['ts'] = time
    cur_settings['target_bit_rate'] = br
    cur_settings['target_bit_rate_upper'] = int(cur_settings['target_bit_rate'] * (1+cur_settings['fluctuation_range']) + 0.5)
    if cur_settings['max_bit_rate'] < cur_settings['target_bit_rate']:
                    cur_settings['max_bit_rate'] = cur_settings['target_bit_rate']
    cur_list.append(cur_settings)

def option_max_br_update(cur_list, time, br):
    cur_settings = cur_list[-1].copy()
    cur_settings['ts'] = time
    cur_settings['max_bit_rate'] = br
    cur_list.append(cur_settings)

def get_derive(vec):
    m1 = vec[1:]
    m2 = vec[0:-1]
    return [v1-v2 for (v1,v2) in zip(m1, m2)]


class cQualityMetricLine(object):
    def __init__(self, name, type=[]):
        self.name = name
        self.type = type
        self.idx = []
        self.val = []
        self.average_value = 0.0
        self.color = None

    def add_data_point(self, idx, val):
        self.idx.append(idx)
        self.val.append(val)

    def add_average(self, val):
        self.average_value = val

    def set_color(self, c):
        self.color = c

    def set_metric_name(self, name):
        self.name = name

    def get_value(self, pos):
        return self.val[pos]

    def get_average(self):
        if self.average_value == 0.0:
            self.average_value = numpy.average(self.val)

        return self.average_value

    def get_var(self):
        return numpy.var(self.val)

    def plot_metric_line(self):
        fig, axes = plt.subplots(1, 1, sharex=True)
        plt.title(self.name + ':' + self.type)
        axes.plot(self.idx, self.val, label=self.type)
        plt.savefig(self.name+'.png')
        plt.show()

