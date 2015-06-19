__author__ = 'sijchen'



class cCurrentEncoding(object):
    def __init__(self, input_cfg_file):
        self.basic_settings = {}
        self.all_settings = []
        self.layer_settings = [{}, {}, {}, {}]
        self.encoding_results = None

        self.basic_setting_file = 'EncodeBasic.cfg'
        # iUsageType = 0,iPicWidth= 1920;iPicHeight= 1088;iTargetBitrate= 5000000;iMaxBitrate= 6000000;iRCMode= 1;iPaddingFlag= 0;iTemporalLayerNum= 3;iSpatialLayerNum= 1;fFrameRate= 12.000000f;uiIntraPeriod= 0;
        # bEnableSpsPpsIdAddition = 1;bPrefixNalAddingCtrl = 0;bEnableDenoise= 0;bEnableBackgroundDetection= 1;bEnableAdaptiveQuant= 1;bEnableFrameSkip= 1;bEnableLongTermReference= 1;iLtrMarkPeriod= 30;
        # iComplexityMode = 1;iNumRefFrame = 4;iEntropyCodingModeFlag = 0;uiMaxNalSize = 0;iLTRRefNum = 2;iMultipleThreadIdc = 1;iLoopFilterDisableIdc = 0
        self.basic_setting_match_re1 = re.compile(r'iUsageType = (\d+),iPicWidth= (\d+);iPicHeight= (\d+);iTargetBitrate= (\d+);iMaxBitrate= (\d+);iRCMode= (\d+);iPaddingFlag= \d+;iTemporalLayerNum= (\d+);iSpatialLayerNum= (\d+);fFrameRate= (\d+.\d+)f;uiIntraPeriod= (\d+)')
        self.basic_setting_match_re2 = re.compile(r'bEnableSpsPpsIdAddition = (\d+);bPrefixNalAddingCtrl = (\d+);bEnableDenoise= (\d+);bEnableBackgroundDetection= (\d+);bEnableAdaptiveQuant= (\d+);bEnableFrameSkip= (\d+);bEnableLongTermReference= (\d+);iLtrMarkPeriod= (\d+)')
        self.basic_setting_match_re3 = re.compile(r'iComplexityMode = (\d+);iNumRefFrame = (\d+);iEntropyCodingModeFlag = (\d+);uiMaxNalSize = (\d+);iLTRRefNum = (\d+);iMultipleThreadIdc = \d+;iLoopFilterDisableIdc = (\d+)')
        self.setting_match_re = re.compile(r'sSpatialLayers\[(\d+)\]: .iVideoWidth= (\d+); .iVideoHeight= (\d+); .fFrameRate= (\d+.\d+)f; .iSpatialBitrate= (\d+); .iMaxSpatialBitrate= (\d+); .sSliceCfg.uiSliceMode= (\d+); .sSliceCfg.sSliceArgument.iSliceNum= (\d+); .sSliceCfg.sSliceArgument.uiSliceSizeConstraint= (\d+)')
        self.read_encoder_basic_settings(self.basic_setting_file)

        self.batch_setting_match_re0 = re.compile(r'EncodeParam(\d+): InputFile = (.*).yuv;iPicWidth= (\d+);iPicHeight= (\d+);fFrameRate= (\d+.\d+)f;iTargetBitrate= (\d+);iMaxBitrate= (\d+)')
        self.batch_settings = []
        self.read_encoder_batch_settings(input_cfg_file)

    def get_basic_settings1(self, r):
        self.basic_settings['usage_type'] = int(r.groups()[0])
        self.basic_settings['width']      = int(r.groups()[1])
        self.basic_settings['height']     = int(r.groups()[2])
        self.basic_settings['target_bit_rate'] = int(r.groups()[3])
        self.basic_settings['max_bit_rate']    = int(r.groups()[4])

        self.basic_settings['rc_mode']         = int(r.groups()[5])
        self.basic_settings['temporal_layers'] = int(r.groups()[6])
        self.basic_settings['spatial_layers']  = int(r.groups()[7])

        self.basic_settings['frame_rate'] = float(r.groups()[8])
        self.basic_settings['intra_period'] = float(r.groups()[9])

    def get_basic_settings2(self, r):
        self.basic_settings['bEnableSpsPpsIdAddition'] = int(r.groups()[0])
        self.basic_settings['bPrefixNalAddingCtrl']    = int(r.groups()[1])
        self.basic_settings['bEnableDenoise']          = int(r.groups()[2])
        self.basic_settings['bEnableBackgroundDetection'] = int(r.groups()[3])
        self.basic_settings['bEnableAdaptiveQuant']    = int(r.groups()[4])

        self.basic_settings['bEnableFrameSkip']         = int(r.groups()[5])
        self.basic_settings['bEnableLongTermReference'] = int(r.groups()[6])
        self.basic_settings['iLtrMarkPeriod']  = int(r.groups()[7])

    def get_basic_settings3(self, r):
        self.basic_settings['iComplexityMode'] = int(r.groups()[0])
        self.basic_settings['iNumRefFrame']    = int(r.groups()[1])
        self.basic_settings['iEntropyCodingModeFlag'] = int(r.groups()[2])
        self.basic_settings['uiMaxNalSize'] = int(r.groups()[3])
        self.basic_settings['iLTRRefNum']    = int(r.groups()[4])
        self.basic_settings['iLoopFilterDisableIdc']         = int(r.groups()[5])

    def get_layer_settings(self, r):
        idx = int(r.groups()[0])
        self.layer_settings[idx]['width'] = int(r.groups()[1])
        self.layer_settings[idx]['height'] = int(r.groups()[2])
        self.layer_settings[idx]['frame_rate'] = float(r.groups()[3])
        self.layer_settings[idx]['target_bit_rate'] = int(r.groups()[4])
        self.layer_settings[idx]['max_bit_rate'] = int(r.groups()[5])
        self.layer_settings[idx]['timewindow'] = BIT_RATE_TIMEWINDOW  # ms
        self.layer_settings[idx]['fluctuation_range'] = 0.1
        self.layer_settings[idx]['target_bit_rate_upper'] = int(self.layer_settings[idx]['target_bit_rate'] * (1+self.layer_settings[idx]['fluctuation_range']) + 0.5)

        self.layer_settings[idx]['slice_mode'] = int(r.groups()[6])
        self.layer_settings[idx]['slice_num'] = int(r.groups()[7])
        self.layer_settings[idx]['slice_size'] = int(r.groups()[8])

    def read_encoder_basic_settings(self, files):
        current_file = open(files, 'rU')
        lines = current_file.readlines()
        for line in lines:
            r = self.basic_setting_match_re1.search(line)
            if r is not None:
                self.get_basic_settings1(r)

                r = self.basic_setting_match_re2.search(line)
                if r is not None:
                    self.get_basic_settings2(r)

                r = self.basic_setting_match_re3.search(line)
                if r is not None:
                    self.get_basic_settings3(r)

                self.all_settings.append(self.basic_settings)
            continue
        current_file.close()

    def read_encoder_batch_settings(self, files):
        current_file = open(files, 'rU')
        lines = current_file.readlines()
        for line in lines:
            r = self.batch_setting_match_re0.search(line)
            if r is not None:
                local_dict = {}
                local_dict['input'] = r.groups()[1]
                local_dict['width'] = int(r.groups()[2])
                local_dict['height'] = int(r.groups()[3])
                local_dict['frame_rate'] = float(r.groups()[4])
                local_dict['target_br'] = int(r.groups()[5])
                local_dict['max_br'] = int(r.groups()[6])
                self.batch_settings.append(local_dict)
            continue
        current_file.close()


    def all_encoding(self, result_file):
        current_results = open(result_file, 'wU')

        for one_setting in self.all_settings:
            bs_name, log_name = call_encoder(one_setting['input'], 0,
                                        one_setting['width'], one_setting['height'], one_setting['frame_rate'],
                                        one_setting['target_br'], one_setting['max_br'])

            os.rename('log.txt', bs_name+'.txt')
            current_results.writelines('Info: Log = %s; Original = %s; BsName = %s; Width = %d; Height = %d'
                   %(bs_name+'.txt', one_setting['input']+'.yuv', bs_name, one_setting['width'], one_setting['height']))

        current_results.close()




"""
"""
def check_one_cfg(cfg_file):
    skip_list = None
    batch_cfg_lines = []
    cbatch_cfg_lines = cBatchPsnr(cfg_file)
    batch_cfg_lines = cbatch_cfg_lines.get_lines()
    if len(batch_cfg_lines) == 0:
        sys.stdout.write("[Option]batch_cfg_lines: cannot find formatted lines! \n "
                         "Example1: Info: Log = (log).txt; Original = (input)_(width)x(height).yuv; BsName = (name).264;\n"
                         "Example2: Info: Log = (log).txt; Original = (input).yuv; BsName = (name).264; Width = (width); Height = (height);")

    for one_line in batch_cfg_lines:
        skip_list = analyze_one_log(one_line[0])
        check_one_case(one_line[2], one_line[1], one_line[3], one_line[4], skip_list)

def analyze_one_log(log_file):
    current_log = cCurrentLog()
    current_log.read_logs(log_file)
    exceed_times_ratio, max_burst_ratio, skip_ratio, skip_successive = current_log.check_bitrate_overflow()

    return exceed_times_ratio, max_burst_ratio, skip_ratio, skip_successive, current_log.get_skip_list()
