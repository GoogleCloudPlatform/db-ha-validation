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

"""Tests for excerptor module that pulls just the changed logs from DB hosts"""
import pathlib
import os
import sys
import json
import datetime
import paramiko
from absl.testing import absltest
from unittest.mock import patch, Mock

# pylint: disable=invalid-name

THIS_DIR = pathlib.Path(__file__).absolute().parent
sys.path.append(str(THIS_DIR.parent))

# pylint: disable-next=import-error,wrong-import-position
from src.common.cm4_excerptor import ExcerptorCls

site_constants_json = "".join([str(THIS_DIR), '/testdata'
                                              '/site_constants'
                                              '.json'])
with open(site_constants_json, encoding="utf-8") as json_constants_fh:
    deserialized_data_inside_test = json.load(json_constants_fh)

# Triple quoted string formats inspired from:
# http://google3/corp/hiring/contrib/code_review_snippets/log_parsing/log_parsing_test.py
_retval_from_wc_l_host_1 = """\
1000 /u01/app/oracle/diag/asm/+asm/+ASM1/trace/alert_+ASM1.log
2000 /u01/app/oracle/diag/crs/at-3793329-svr005/crs/trace/alert.log
3000 /u01/app/oracle/diag/rdbms/orcl/orcl1/trace/alert_orcl1.log
117562 total
"""

_retval_from_wc_l_host_2 = """\
100 /u01/app/oracle/diag/asm/+asm/+ASM2/trace/alert_+ASM2.log
200 /u01/app/oracle/diag/crs/at-3793329-svr006/crs/trace/alert.log
300 /u01/app/oracle/diag/rdbms/orcl/orcl2/trace/alert_orcl2.log
117562 total
"""

expected_tail_cmds_dict = {
    '172.16.110.1': [
        ('/u01/app/oracle/diag/asm/+asm/+ASM1/trace/alert_+ASM1.log', '1000'),
        ('/u01/app/oracle/diag/crs/at-3793329-svr005/crs/trace/alert.log',
         '2000'),
        ('/u01/app/oracle/diag/rdbms/orcl/orcl1/trace/alert_orcl1.log',
         '3000')],
    '172.16.110.2': [
        ('/u01/app/oracle/diag/asm/+asm/+ASM2/trace/alert_+ASM2.log', '100'),
        ('/u01/app/oracle/diag/crs/at-3793329-svr006/crs/trace/alert.log',
         '200'),
        (
        '/u01/app/oracle/diag/rdbms/orcl/orcl2/trace/alert_orcl2.log', '300')],
}

# prefill the contents of the 6 local files that will contain contents from
# the 6 remote alerts logs as noted in the preceding dict

_contents_1 = """\
Tell her to reap it with a sickle of leather
-Blazing in scarlet battalions
Parsley, sage, rosemary, and thyme
-Generals order their soldiers to kill
And gather it all in a bunch of heather
-A cause they've long ago forgotten
Then she'll be a true love of mine
"""

_contents_2 = """\
If you can dream—and not make dreams your master;
   If you can think—and not make thoughts your aim;
If you can meet with triumph and disaster
   And treat those two impostors just the same;
"""

_contents_3 = """\
The woods are lovely, dark and deep.
But I have promises to keep,
And miles to go before I sleep,
And miles to go before I sleep.
"""

_contents_4 = """\
I wandered lonely as a cloud
That floats on high o'er vales and hills,
When all at once I saw a crowd,
A host, of golden daffodils;
"""

_contents_5 = """\
I saw a film today, oh boy
The English Army had just won the war
A crowd of people turned away
But I just had to look
"""

_contents_6 = """\
To be, or not to be, that is the question:
Whether 'tis nobler in the mind to suffer
The slings and arrows of outrageous fortune,
Or to take arms against a sea of troubles
"""

mocked_stdin_channel = Mock(spec=paramiko.channel.ChannelStdinFile)
mocked_stderr_channel = Mock(spec=paramiko.channel.ChannelStderrFile)
mocked_stdin_channel.read.return_value = b''
mocked_stderr_channel.read.return_value = b'Leave No Man Behind-Zimmer'

mocked_stdout_channel1 = Mock(spec=paramiko.channel.ChannelFile)
mocked_stdout_channel2 = Mock(spec=paramiko.channel.ChannelFile)
mocked_stdout_channel3 = Mock(spec=paramiko.channel.ChannelFile)
mocked_stdout_channel4 = Mock(spec=paramiko.channel.ChannelFile)
mocked_stdout_channel5 = Mock(spec=paramiko.channel.ChannelFile)
mocked_stdout_channel6 = Mock(spec=paramiko.channel.ChannelFile)
mocked_stdout_channel1.read.return_value = bytes(_contents_1, 'utf-8')
mocked_stdout_channel2.read.return_value = bytes(_contents_2, 'utf-8')
mocked_stdout_channel3.read.return_value = bytes(_contents_3, 'utf-8')
mocked_stdout_channel4.read.return_value = bytes(_contents_4, 'utf-8')
mocked_stdout_channel5.read.return_value = bytes(_contents_5, 'utf-8')
mocked_stdout_channel6.read.return_value = bytes(_contents_6, 'utf-8')


class TestExcerptorCls(absltest.TestCase):
    """Test excerptor methods and logs excerption.

    The tests below will verify that the public methods of ExcerptorCls() will
    correctly construct the dictionary of high watermarks and then use that to
    excerpt the remote files appropriately into the local files.
    """

    @classmethod
    def setUp(cls) -> None:
        super(TestExcerptorCls, cls)  # go/gpylint-faq#g-missing-super-call
        cls.run_id = datetime.datetime.now().strftime('%s_%b%d%y_%H%M%S')
        cls.log_location = "".join([str(THIS_DIR), '/testdata/logs/'])
        cls.expected_paths = [
            ''.join([cls.log_location, cls.run_id, '_node1_asm_log']),
            ''.join([cls.log_location, cls.run_id, '_node1_crs_log']),
            ''.join([cls.log_location, cls.run_id, '_node1_db_log']),
            ''.join([cls.log_location, cls.run_id, '_node2_asm_log']),
            ''.join([cls.log_location, cls.run_id, '_node2_crs_log']),
            ''.join([cls.log_location, cls.run_id, '_node2_db_log']),
        ]

    @classmethod
    def tearDown(cls) -> None:
        # garbage collect the swingbench_obj instance after tests
        cls.ExcerptorCls_obj = None

        # remove the excerpted local files generated for the tests
        # needed to not spam tests/testdata with files generated for tests

        for path in cls.expected_paths:
            if os.path.exists(path):
                pathlib.Path(path).unlink()

        super(TestExcerptorCls, cls)  # go/gpylint-faq#g-missing-super-call

    # mock the paramiko call and mock the return value from wc -l
    # and confirm that the instance attr tail_cmds_dict is as you expect
    @patch("src.common.cm6_paramiko.RSAKey", spec=True)
    @patch('src.common.cm1_json_file_flag.deserialized_data',
           deserialized_data_inside_test)
    @patch('src.common.cm6_paramiko.ClientCls.store_op_to_py_variables',
           side_effect=[_retval_from_wc_l_host_1, _retval_from_wc_l_host_2])
    @patch('src.common.cm6_paramiko.SSHClient', spec=True)
    def test_inst_attr_for_mocked_ssh_returnvalue(self,
                                                  mocked_paramiko_sshclient,
                                                  mocked_ClientCls,
                                                  mocked_rsakey,
                                                  ):
        """Confirm that the instance attr tail_cmds_dict is built as expected.

        Given a series of return strings from the DB backends as the result of
        the high watermark probe command `wc -l`, test that the method
        generate_get_hwm_groupby_host() correctly constructs the instance attr
        `tail_cmds_dict` based on the foll. returned SSH o/p from remote hosts:
        _retval_from_wc_l_host_1
        _retval_from_wc_l_host_2

        The mock objects used are:
        1) src.common.cm6_paramiko.RSAKey => so, we don't need an actual
        working private key stored in the path specified by the key
        `ssh_key_file` in `site_constants.json`
        2) src.common.cm1_json_file_flag.deserialized_data => so the tests can
        be run independent of any customer/site specific DB node specifics
        where tests are dependent only on the site_constant.json that comes
        packaged with the testdata/ folder contents
        3) src.common.cm6_paramiko.ClientCls.store_op_to_py_variables => to
        mock the returned string from paramiko SSHClient processed into a str
        by ClientCls().store_op_to_py_variables method. We use side_effect
        with a iterable/list of 2 return values instead of return_value because
        cm6_paramiko.ClientCls.store_op_to_py_variables is called in a `for`
        that iterates 2 times. If we used return value like:
        return_value=_retval_from_wc_l_host_1 , the resulting tail_cmds_dict
        will have repeated values for both host_ip keys.
        4) src.common.cm6_paramiko.SSHClient => mock the connection to an
        external SSH host that is outside the boundary of the code being tested
        """
        ExcerptorCls_obj = ExcerptorCls(self.run_id, self.log_location)
        ExcerptorCls_obj.generate_get_hwm_groupby_host()

        self.assertEqual(ExcerptorCls_obj.tail_cmds_dict,
                         expected_tail_cmds_dict)

    # setup test so that you have a file full of song lyrics
    # and simulated HWM is at a given point in the file...assert lines written
    # to local file has those contents

    # assert local file names are created as intended in generate_*() method
    # assert that there are 6 files created under testdata as per site
    # constants json file
    @patch("src.common.cm6_paramiko.RSAKey", spec=True)
    @patch('src.common.cm1_json_file_flag.deserialized_data',
           deserialized_data_inside_test)
    @patch('src.common.cm6_paramiko.ClientCls.store_op_to_py_variables',
           side_effect=[_retval_from_wc_l_host_1, _retval_from_wc_l_host_2])
    @patch('src.common.cm6_paramiko.ClientCls.run_remote_cmd',
           side_effect=[(mocked_stdout_channel1, mocked_stderr_channel),
                        (mocked_stdout_channel2, mocked_stderr_channel),
                        (mocked_stdout_channel3, mocked_stderr_channel),
                        (mocked_stdout_channel4, mocked_stderr_channel),
                        (mocked_stdout_channel5, mocked_stderr_channel),
                        (mocked_stdout_channel6, mocked_stderr_channel)
                        ])
    @patch('src.common.cm6_paramiko.SSHClient', spec=True)
    def test_logs_excerpted_with_mocked_ssh_returnvalue(self,
                                                        mocked_paramiko_sshclient,
                                                        mocked_ClientCls_run_remote_cmd,
                                                        mocked_ClientCls_store_op_method,
                                                        mocked_rsakey,
                                                        ):
        """Test excerpt_logs() correctly excerpts remote files into local files

        The mock objects are same as previous with the addition of:
        src.common.cm6_paramiko.ClientCls.run_remote_cmd => we are replacing
        the output of the SSH with known Paramiko stdin file contents. As
        before usage:
        @patch('src.common.cm6_paramiko.ClientCls.run_remote_cmd',
           return_value=(mocked_stdout_channel1, mocked_stderr_channel)
        will result in all the local files created with same content, which we
        avoid by feeding a iterable into side_effect that reflects real-life
        results of getting 6 different file excepts (ASM, CRS, DB alert logs
        from 2 RAC nodes)

        """
        ExcerptorCls_obj = ExcerptorCls(self.run_id, self.log_location)
        ExcerptorCls_obj.generate_get_hwm_groupby_host()
        ExcerptorCls_obj.excerpt_logs()

        # verify if all the 6 remote files have been excerpted locally
        for path in self.expected_paths:
            self.assertTrue(os.path.exists(path),
                            msg=''.join([path, ' does not exist']))

        # verify if file content is what is expected
        # spot checking subset of files instead of all 6 for brevity
        with open(''.join([self.log_location, self.run_id, '_node1_asm_log']),
                  'r', encoding='utf-8') as file_handle:
            content_to_grep = ('-Blazing in scarlet battalions\n'
                               'Parsley, sage, rosemary, and thyme')

            self.assertTrue(content_to_grep in file_handle.read())

        with open(''.join([self.log_location, self.run_id, '_node2_crs_log']),
                  'r', encoding='utf-8') as file_handle:
            content_to_grep = 'The English Army had just won the war'

            self.assertTrue(content_to_grep in file_handle.read())

        with open(''.join([self.log_location, self.run_id, '_node1_crs_log']),
                  'r', encoding='utf-8') as file_handle:
            content_to_grep = 'If you can meet with triumph and disaster'

            self.assertTrue(content_to_grep in file_handle.read())
            file_handle.seek(0)
            self.assertNotIn('scarborough fair', file_handle.read())


if __name__ == '__main__':
    absltest.main()
