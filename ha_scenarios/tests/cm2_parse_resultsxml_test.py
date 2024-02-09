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

"""Tests for parser module that processes xml output file from Swingbench"""
import pathlib
import sys
from absl.testing import absltest

THIS_DIR = pathlib.Path(__file__).absolute().parent
sys.path.append(str(THIS_DIR.parent))
from src.common.cm2_parse_resultsxml import ParseSwingbenchRunXML  # pylint: disable=import-error,wrong-import-position

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


class TestParseSwingbenchXML(absltest.TestCase):
    """ Test parser logic supplying files generated from actual runs """
    def test_calculatedoutage_xmlfile1(self):
        " Assert calculated outage equals actual outage duration"
        sample_xml_filename = THIS_DIR/'testdata/1661415592_Aug2522_011952.xml'

        instance_parse_swingbench_run_xml_cls = ParseSwingbenchRunXML(
            resultsxml_file=sample_xml_filename)
        instance_parse_swingbench_run_xml_cls.parse_swingbench_resultsxml()

        self.assertEqual(instance_parse_swingbench_run_xml_cls.workload_start,
                         1661415598772)
        self.assertEqual(instance_parse_swingbench_run_xml_cls.outage_start,
                         1661415685790)
        self.assertEqual(instance_parse_swingbench_run_xml_cls.outage_end,
                         1661415687790)

        self.assertEqual(instance_parse_swingbench_run_xml_cls.outage_duration,
                         2.0)  # (1661415687790 - 1661415685790) / 1000

    def test_calculatedoutage_xmlfile2(self):
        " Assert calculated outage equals actual outage duration"
        sample_xml_filename = THIS_DIR/'testdata/1658003923_Jul1622_133843.xml'

        instance_parse_swingbench_run_xml_cls = ParseSwingbenchRunXML(
            resultsxml_file=sample_xml_filename)
        instance_parse_swingbench_run_xml_cls.parse_swingbench_resultsxml()
        self.assertEqual(instance_parse_swingbench_run_xml_cls.workload_start,
                         1658003959828)
        self.assertEqual(instance_parse_swingbench_run_xml_cls.outage_start,
                         1658004016839)
        self.assertEqual(instance_parse_swingbench_run_xml_cls.outage_end,
                         1658004072851)
        self.assertEqual(instance_parse_swingbench_run_xml_cls.outage_duration,
                         (1658004072851 - 1658004016839) / 1000)

    def test_calculatedoutage_xmlfile3(self):
        " Assert calculated outage equals actual outage duration"
        sample_xml_filename = THIS_DIR/'testdata/1658297854_Jul1922_231734.xml'

        instance_parse_swingbench_run_xml_cls = ParseSwingbenchRunXML(
            resultsxml_file=sample_xml_filename)
        instance_parse_swingbench_run_xml_cls.parse_swingbench_resultsxml()
        self.assertEqual(instance_parse_swingbench_run_xml_cls.workload_start,
                         1658297891190)
        self.assertEqual(instance_parse_swingbench_run_xml_cls.outage_start,
                         1658297948201)
        self.assertEqual(instance_parse_swingbench_run_xml_cls.outage_end,
                         1658298005214)
        self.assertEqual(instance_parse_swingbench_run_xml_cls.outage_duration,
                         57.013)  # (1658298005214 - 1658297948201) / 1000)

    def test_calculatedoutage_xmlfile4(self):
        " Assert calculated outage equals actual outage duration"
        sample_xml_filename = THIS_DIR/'testdata/1658452689_Jul2122_181809.xml'

        instance_parse_swingbench_run_xml_cls = ParseSwingbenchRunXML(
            resultsxml_file=sample_xml_filename)
        instance_parse_swingbench_run_xml_cls.parse_swingbench_resultsxml()
        self.assertEqual(instance_parse_swingbench_run_xml_cls.workload_start,
                         1658452696026)
        self.assertEqual(instance_parse_swingbench_run_xml_cls.outage_start,
                         1658452864056)
        self.assertEqual(instance_parse_swingbench_run_xml_cls.outage_end,
                         1658453729205)
        self.assertEqual(instance_parse_swingbench_run_xml_cls.outage_duration,
                         865.149)  # (1658453729205 - 1658452864056) / 1000)


if __name__ == '__main__':
    absltest.main()
