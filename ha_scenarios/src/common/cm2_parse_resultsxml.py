#!/usr/bin/python
#
# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Module that parses output of Swingbench run to calculate outage duration."""
import xml.etree.ElementTree as ET
import datetime
import pathlib

'''
1)
Ignoring `too-few-public-methods` as that guidance is not best applicable to here due to the 
design of all common modules. In our specific case, we need the instance method wrapped in 
a class that does the parsing logic for us so the data struct can be used/retained across modules 
(as will be seen when we are at a point to review a fully featured failure scenario).

2)
Ignoring: `too-many-instance-attributes`: 
self.workload_start_tm ,
self.outage_start_tm,
self.outage_end_tm,
self.outage_duration
are needed outside for logging and the values of self.workload_start,self.outage_start
and self.outage_end` are needed in the unit testing code.
'''

class ParseSwingbenchRunXML:  # pylint: disable=too-few-public-methods,too-many-instance-attributes
    """ Exposes instance methods that parses Swingbench benchmarking output (xml) file.

    Every Swingbench run done via CLI results in a benchmarking output file in xml format.
    The tag of interest for parsing the data from the xml file is <BenchmarkMetrics>/<TPSReadings> 
    A trimmed version of the generated xml file will be something like:

    <?xml version = '1.0' encoding = 'UTF-8'?>
    <Results xmlns="http://www.dominicgiles.com/swingbench">
       ...
       <BenchmarkMetrics>
          <TPSReadings>1658003925819, 0,1658003926819, 0,1658003927819, 0,1658003928820, 0,
          1658003929820, 0,1658003930820, 0,1658003931820, 0,1658003932821, 0,...,
          1658003963829, 127,1658003964829, 113,1658003965829, 124,1658003966829, 114,
          1658003967830, 114,1658003968830, 118,1658003969830, 122,1658003970830, 124,
          1658003971830, 113,1658003972831, ..., 1658004016839, 0,1658004017839, 0,
          1658004018839, 0,1658004019840, 0,1658004020840, 0,1658004021840, 0,1658004022840, 0,
          1658004023840, 0,1658004024841, 0,1658004025841, 0,1658004026841, 0,1658004027841, 0,
          1658004028842, 0,1658004029842, 0,1658004030842, 0,1658004031842...,1658004074851, 116,
          1658004075852, 120,...1658005424067, 122,</TPSReadings>
       </BenchmarkMetrics>
    </Results>

    The TPS is a timeseries tuple of the form (epoch timestamp, TPS). The Swingbench run has these
    exact well-defined/observed states:
    1) Initial ramp up when the TPS data is 0
    2) Full ramped up when the TPS data holds steady
    3) Fault injection when the TPS data hits 0, this is the start of the outage
    4) Full recovery when TPS data goes back to pre-fault-injection level, this is the end of outage

    The exposed instance method `parse_swingbench_resultsxml` parses the generated xml file and 
    calculates the outage duration for a given failure injection scenario.

    An example invocation of the functionalities provided by this class may be
    as follows:

    instance_parse_swingbench = ParseSwingbenchRunXML(resultsxml_file=sample_xml_filename)
    instance_parse_swingbench.parse_swingbench_resultsxml()


    """
    def __init__(self, resultsxml_file: str):
        self.resultsxml_file = resultsxml_file
        self.workload_start = 0
        self.outage_start = 0
        self.outage_end = 0
        self.workload_start_tm = None
        self.outage_start_tm = None
        self.outage_end_tm = None
        self.outage_duration = None

    def parse_swingbench_resultsxml(self) -> None:
        """Instance method that does parsing"""
        tree = ET.parse(self.resultsxml_file)

        root = tree.getroot()

        # https://docs.python.org/3/library/xml.etree.elementtree.html#example
        for i in root.findall('.//{http://www.dominicgiles.com/swingbench'
                              '}TPSReadings'):
            # [:-1] to remove the trailing comma that's always in the swingbench data
            if i.text[-1] == ",":
                csv_timeseries = i.text[:-1]

        # ts_list = csv_timeseries.split(",")
        ts_list = [int(i) for i in csv_timeseries.split(",")]  # list comprehension conversion

        idx_end = len(ts_list) - 1

        for i in range(0, idx_end, 2):
            # Till Swingbench ramps up, the TPS will be all 0s initially
            if ts_list[i + 1] != 0 and self.outage_start == 0 \
                    and self.workload_start == 0:
                self.workload_start = ts_list[i]
            # after a series of non-zero TPS, the outage contains a value of
            # 0 for the TPS
            elif ts_list[i + 1] == 0 and self.outage_start == 0 \
                    and self.workload_start != 0:
                self.outage_start = ts_list[i]
            # after a series of zero TPS, a non-zero value of TPS > 100
            # indicates end of outage the non-zero TPS continues till the
            # end of the swingbench test, so exit after traversing the first
            # non-zero
            elif ts_list[i + 1] > 100 and self.outage_start != 0 \
                    and self.workload_start != 0:
                self.outage_end = ts_list[i]
                break  # exit after encountering the first timestamp that
                # specifies end of outage with non-zero TPS

        self.workload_start_tm = datetime.datetime.fromtimestamp(
            self.workload_start / 1000)
        self.outage_start_tm = datetime.datetime.fromtimestamp(
            self.outage_start / 1000)
        self.outage_end_tm = datetime.datetime.fromtimestamp(
            self.outage_end / 1000)
        self.outage_duration = (self.outage_end - self.outage_start) / 1000

        # print statement for helping with reviews, will be converted to logger
        # once logger class is reviwed and merged into codebase
        print(
            f'workload_start: {self.workload_start}, '
            f'outage_start:{ self.outage_start}, '
            f'outage_end: {self.outage_end}, '
            f'workload_start_tm: {self.workload_start_tm}, '
            f'outage_start_tm: {self.outage_start_tm}, '
            f'outage_end_tm: {self.outage_end_tm}, '
            f'outage_duration: {self.outage_duration} secs')


def parser_standalone_runner():
    """ standalone runner to run this module as a script independently """

    THIS_DIR = pathlib.Path(__file__).absolute().parent # pylint: disable=invalid-name

    sample_xml_filename = THIS_DIR/'../../tests/testdata/1661415592_Aug2522_011952.xml'

    instance_parse_swingbench = ParseSwingbenchRunXML(
        resultsxml_file=sample_xml_filename)
    instance_parse_swingbench.parse_swingbench_resultsxml()


if __name__ == '__main__':
    parser_standalone_runner()
