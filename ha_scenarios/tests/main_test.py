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

import json
import os
import pathlib
import sys

from absl import flags
from absl.testing import flagsaver
from absl.testing import absltest
from unittest.mock import patch

# import module under test: main.py from ./..
sys.path.append(str(pathlib.Path(__file__).absolute().parent.parent))
import main
from src.common import cm1_json_file_flag


FLAGS = flags.FLAGS
_initial_flag_values = flagsaver.save_flag_values()  # (1) => flags have
# default values, ex.: scenario = None

# Initialize required flags. See: yaqs/5785549575028736 and
# yaqs/41383418646233088
FLAGS.json_file = ''
FLAGS.scenario = ''

os.chdir(sys.path[0])
# to access the testdata/site_constants.json file
# irrespective of from where the test is called from


class TestProcessInputFlags(absltest.TestCase):
    def setUp(self):
        super().setUp()
        flagsaver.restore_flag_values(_initial_flag_values)

    # test if the directory created by a function in main.py corresponds to
    # what we passed in as --log_dest flag
    @flagsaver.flagsaver(json_file='testdata/site_constants.json',
                         scenario='testing', log_dest='/tmp')
    @patch('main.run_id', 'XXX')
    def test_flag_log_dest_creates_dir(self):
        main.process_input_flags()

        expected_path = "/tmp/XXX_testing"
        # Pattern:
        # "".join([FLAGS.log_dest, '/', main._RUN_ID, "_", FLAGS.scenario])
        self.assertTrue(os.path.exists(expected_path),
                        msg="".join([expected_path, " does not exist"]))

    # test if the contents of json file input via --json_file flag is
    # correctly deserialized by python into a dict
    @flagsaver.flagsaver(json_file='testdata/two_element.json',
                         node_ip_to_test='172.16.110.1', scenario='testing')
    def test_flag_json_file_deserialization(self):
        # create a two-element json file and check if the dict processed by
        # process_input_flags() namely deserialized_data matches the json
        # file created using assertDictEqual
        simple_dict = {"a": 1, "b": 2}
        with open("testdata/two_element.json", "w") as write_file:
            json.dump(simple_dict, write_file)
        main.process_input_flags()
        self.assertDictEqual(cm1_json_file_flag.deserialized_data, simple_dict)

    # test that when optional --node_ip_to_test is omitted (None), correct
    # dictionary element is picked for NODE_TO_TEST from input json file. We
    # test this atomically by creating a simple 2 element jsonfile &
    # omitting --node_ip_to_test
    @flagsaver.flagsaver
    def test_flag_node_ip_to_test(self):
        FLAGS.node_ip_to_test = None
        FLAGS.scenario = 'testing'
        FLAGS.json_file = '/tmp/test_json.json'
        simple_dict = {"nodes": [{"host_ip": "172.16.110.1"},
                                 {"host_ip": "172.16.110.2"}]}
        with open("/tmp/test_json.json", "w") as write_file:
            json.dump(simple_dict, write_file)
        main.process_input_flags()
        self.assertEqual(main.NODE_TO_TEST, "172.16.110.2")

    # test if scenario flag is triggering the correct function call in main.py
    @flagsaver.flagsaver(json_file='/tmp/test_json.json', log_dest='/tmp',
                         scenario='testing')
    @patch("main._scenario_testing")
    def test_flag_scenario_appropriate_function_called(self, mock_method):
        main.main(argv=None)
        # print(mock_method.called, mock_method.call_args_list)
        # print(mock_method.called, mock_method.call_args_list)
        self.assertTrue(mock_method.called)

    # test if scenario flag is triggering the correct function call in main.py
    @flagsaver.flagsaver(json_file='/tmp/test_json.json', log_dest='/tmp',
                         scenario='testingasdfasdfasd')
    @patch("main._scenario_testing")
    def test_flag_scenario_appropriate_function_not_called(self, mock_method):
        main.main(argv=None)
        self.assertFalse(mock_method.called)


if __name__ == '__main__':
    absltest.main()
