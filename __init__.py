

TMP_FOLDER = "/Users/sijchen/WorkingCodes/TestSequences/tmp"
CAMERA_SEQ_PATH = "/Users/sijchen/WorkingCodes/TestSequences/CameraTypical"
SCREEN_SEQ_PATH = "/Users/sijchen/WorkingCodes/TestSequences/ScreenTypical"
#Add by guangwei
TEST_SEQ_PATH = '/Users/guangwwa/WorkSpace/TestSequences/'
OUT_DATA_PATH = '/Users/guangwwa/WorkSpace/IOdata/'
TOOLS_PATH = '/Users/guangwwa/WorkSpace/Tools/'

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

