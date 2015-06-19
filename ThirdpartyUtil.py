import os, sys
import subprocess
import csv
from RateControlUtil import cQualityMetricLine

DEBUG = 1

class cVqmtTool(object):
    def __init__(self, path):
        self.path = path

    def read_results_from_csv(self, output_name, type):
        csv_name = output_name+'_' + type + '.csv'
        if DEBUG:
            dir = os.getcwd()
            sys.stdout.write("Reading %s\n" %(dir + os.sep + csv_name) )
        csv_file = open(csv_name, 'r')
        reader = csv.reader(csv_file, dialect='excel')
        current_metric_line = cQualityMetricLine(output_name, type)
        for row in reader:
            if row[1] == 'inf':
                current_metric_line.add_data_point(0)
            if row[0] != 'frame' and row[0] != 'average':
                current_metric_line.add_data_point(int(row[0]), float(row[1]))
            if row[0] == 'average':
                current_metric_line.add_average(float(row[1]))
        csv_file.close()
        return current_metric_line



    def compare(self, original, compare_object, width, height, frames, output_name):
        cmdline = str('%s %s %s %d %d %d 1 %s PSNR SSIM'
                    % ('./vqmt', original, compare_object, height, width, frames,
                       output_name))
        p = subprocess.Popen(cmdline, stderr=subprocess.PIPE, shell=True)
        print(p.communicate()[1])
        metric_line = \
            self.read_results_from_csv(output_name, 'psnr')
        metric_line.plot_metric_line()
        return metric_line
