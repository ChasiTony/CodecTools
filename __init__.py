
import config

TMP_FOLDER = config.TMP_FOLDER
CAMERA_SEQ_PATH = config.CAMERA_SEQ_PATH
SCREEN_SEQ_PATH = config.SCREEN_SEQ_PATH

JM_PATH=config.JM_PATH
PSNR_PATH=config.PSNR_PATH

OUT_DATA_PATH = config.OUT_DATA_PATH



def get_did_from_resolution(width, height):
    reso = width+height
    if reso >= (960+540):
        return 3
    elif reso >= (960+540):
        return 2
    elif reso >= (320+180):
        return 1
    else:
        return 0

