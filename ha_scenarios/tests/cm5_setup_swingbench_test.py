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
import os
import json
import datetime
from absl.testing import absltest
from unittest.mock import patch


THIS_DIR = pathlib.Path(__file__).absolute().parent
sys.path.append(str(THIS_DIR.parent))
from src.common.cm5_setup_swingbench import Swingbench


site_constants_json = "".join([str(THIS_DIR), '/testdata'
                                              '/site_constants'
                                              '.json'])
with open(site_constants_json, encoding="utf-8") as json_constants_fh:
    deserialized_data_inside_test = json.load(json_constants_fh)


class TestSwingbenchSetup(absltest.TestCase):
    """Test args generated for Swingbench & test if instance method called"""

    @classmethod
    def setUp(cls) -> None:
        cls.rt_hhmm = '00:02'
        cls.run_id = datetime.datetime.now().strftime('%s_%b%d%y_%H%M%S')
        cls.log_location = "".join([str(THIS_DIR), '/testdata/logs/'])
        cls.site_constants_json = "".join([str(THIS_DIR), '/testdata'
                                                          '/site_constants'
                                                          '.json'])

        cls.expected_path = ''.join(
            [cls.log_location, cls.run_id, '_swingbench_timeseries'])

    @classmethod
    def tearDown(cls) -> None:
        # garbage collect the swingbench_obj instance after tests
        cls.swingbench_obj = None

    # code under test has a method to `generate_swingbench_tokens`
    # following test verifies that generated tokens contain the keys in the
    # mocked cm1_json_file_flag.deserialized_data
    @patch('src.common.cm1_json_file_flag.deserialized_data',
           deserialized_data_inside_test)
    def test_swingbench_mock_modulelevel_variable(self):
        """ deserialized_data_inside_test stands in for the foll. assignment:

        self.deserialized_data = cm1_json_file_flag.deserialized_data
        inside the code under test, ie in: cm5_setup_swingbench.py.

        returned_tokens will be similar to:
        ['/home/user/swingbench/swingbench/bin/charbench', 
        '-c', '/home/user/swingbench/swingbench/configs/soepdb.xml', 
        '-r', '/usr/logs/1674799528_Jan2623_220528.xml',
        '-rt', '00:02', '-a', '-v', '-nc']

        """
        sb_obj = Swingbench(self.rt_hhmm, self.run_id, self.log_location)
        returned_tokens = sb_obj.generate_swingbench_tokens()
        self.assertIn(
            deserialized_data_inside_test["swingbench_binary_location"],
            returned_tokens)
        self.assertIn(
            deserialized_data_inside_test["swingbench_config_file"],
            returned_tokens)

    # code under test has a method to `run_swingbench`
    # mock the Popen inside the method and verify that:
    # subprocess.Popen was called with known list of arguments
    @patch('src.common.cm5_setup_swingbench.Popen', spec=True)
    @patch('src.common.cm1_json_file_flag.deserialized_data',
           deserialized_data_inside_test)
    def test_mock_Popen(self, mocked_Popen):
        """ mocked_Popen is a mock object standing in for subprocess.Popen 

        dir(mocked_Popen) has union of methods from mock and Popen due to spec=True:
        'assert_any_call', 'assert_called', 'assert_called_once', 'assert_called_once_with', 
        'assert_called_with', 'assert_has_calls', 'assert_not_called', 'attach_mock', 'call_args', 
        'call_args_list', 'call_count', 'called', 'communicate', 'configure_mock', 'kill', 
        'method_calls', 'mock_add_spec', 'mock_calls', 'poll', 'reset_mock', 
        'return_value', 'send_signal', 'side_effect', 'terminate', 'universal_newlines', 'wait

        mocked_Popen.call_args will be similar to:
        call(['/home/user/swingbench/swingbench/bin/charbench', 
        '-c', '/home/user/swingbench/swingbench/configs/soepdb.xml', 
        '-r', '/usr/logs/1674799528_Jan2623_220528.xml', 
        '-rt', '00:02', '-a', '-v', '-nc'], 
        stdout=<_io.TextIOWrapper name='/usr/logs/1674799528_Jan2623_220528_swingbench_timeseries' 
        mode='a' encoding='utf-8'>)

        """
        sb_obj = Swingbench(self.rt_hhmm, self.run_id, self.log_location)
        returned_tokens = sb_obj.generate_swingbench_tokens()
        sb_obj.run_swingbench(returned_tokens)
        self.assertListEqual(mocked_Popen.call_args[0][0], returned_tokens)

        self.assertTrue(mocked_Popen.assert_called)
        self.assertTrue(mocked_Popen.call_count, 1)

    # pseudo-mock swingbench binary with a builtin like echo. This is to
    # test: that the subprocess.Popen call actually happens against the
    # builtin instead of against the swingbench binary.
    @patch('src.common.cm1_json_file_flag.deserialized_data',
           deserialized_data_inside_test)
    def test_mock_swingbench_binary_with_builtin(self):
        """ Reason for builtin substitution in place of swingbench binary:

        We don't expect the tester's env to have full-blown Swingbench config.
        Verify that: subprocess.Popen was called with known list of arguments
        recorded in the file that stdout writes to.

        sb_obj.swingbench_cmd_tokens or the returned_tokens before manipulating 
        as part of the test is:
        ['/home/user/swingbench/swingbench/bin/charbench', 
        '-c', '/home/user/swingbench/swingbench/configs/soepdb.xml', 
        '-r', '/usr/logs/1674799528_Jan2623_220528.xml',
        '-rt', '00:02', '-a', '-v', '-nc']


        sb_obj.swingbench_cmd_tokens or the returned_tokens after manipulating 
        as part of the test is:
        ['/usr/bin/echo', 'The swingbench_cmd_tokens is: \n ', 
        '-c', '/home/user/swingbench/swingbench/configs/soepdb.xml', 
        '-r', '/usr/logs/1674799528_Jan2623_220528.xml',
        '-rt', '00:02', '-a', '-v', '-nc']
        """
        sb_obj = Swingbench(self.rt_hhmm, self.run_id, self.log_location)
        returned_tokens = sb_obj.generate_swingbench_tokens()
        returned_tokens[0] = "/usr/bin/echo"  # pseudo-mock
        returned_tokens.insert(1, "The swingbench_cmd_tokens "
                                               "is: \n ")
        sb_obj.run_swingbench(returned_tokens) 
        # we are ensuring above that /usr/bin/echo is run in place of swingbench binary
        # and the necessary swingbench timeseries file is created

        self.assertTrue(os.path.exists(self.expected_path),
                        msg="".join([self.expected_path, " does not exist"]))



if __name__ == '__main__':
    absltest.main()
