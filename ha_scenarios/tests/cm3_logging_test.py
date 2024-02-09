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
import datetime
from absl.testing import absltest

# pylint: disable=invalid-name
# Naming consistent with other modules
THIS_DIR = pathlib.Path(__file__).absolute().parent
sys.path.append(str(THIS_DIR.parent))
# pylint: disable-next=import-error,wrong-import-position
from src.common.cm3_logging import logger_name, LoggerCls


class TestLogging(absltest.TestCase):
    """Test logger using `assertLogs` context manager & actual o/p log file"""

    @classmethod
    def setUp(cls):
        super(TestLogging, cls)  # go/gpylint-faq#g-missing-super-call
        # construct the logfile name that will be generated
        # ex.: tests/testdata/1657669952_Jul1222_165232_runlog
        # logfile name will be accessed inside tests & will be an instance attr

        RUN_ID = datetime.datetime.now().strftime('%s_%b%d%y_%H%M%S')
        LOG_LOCATION = "".join([str(THIS_DIR), '/testdata/logs/'])

        # Following two variables are set up as instance variables
        # to be accessed in the tests and tearDown methods
        cls.logger_obj = LoggerCls(RUN_ID, LOG_LOCATION)
        cls.expected_path = ''.join(
            [LOG_LOCATION, RUN_ID, '_runlog'])

    @classmethod
    def tearDown(cls) -> None:
        # close the logger channels after each test
        # needed so that the multiple tests do not duplicate log entries
        # https://stackoverflow.com/a/69334391/18575251

        # The handlers in cls.logger_obj.logger.handlers are as follows:
        # [<StreamHandler <stdout> (INFO)>,
        # <FileHandler /home/user/167225987_Dec2822_123447_runlog (INFO)>]
        while cls.logger_obj.logger.handlers:
            fh = cls.logger_obj.logger.handlers.pop()
            fh.close()
            # Close the fh avoid:
            # ResourceWarning: unclosed file <_io.TextIOWrapper name='/home/
            # user/167225987_Dec2822_123447_runlog' mode='a' encoding='UTF-8'>


        # remove the logfile generated for the tests
        # needed to not spam tests/testdata with logfiles generated for testing
        pathlib.Path(cls.expected_path).unlink()

        super(TestLogging, cls)  # go/gpylint-faq#g-missing-super-call

    def test_log_with_assertlog_contextmanager(self):
        """Assert logged string is contained in logger using context mgr"""

        # invoke assertlogs context manager to hold the text being logged
        with self.assertLogs('src.common.cm3_logging',
                             level='INFO') as cntxt_mgr:
            self.logger_obj.logger.info('info sir')
            logger_name.warning('warning msg')  # test via module variable
            self.logger_obj.logger.error('tis the error')

        self.assertEqual(cntxt_mgr.output,
                         ['INFO:src.common.cm3_logging:info sir',
                          'WARNING:src.common.cm3_logging:warning msg',
                          'ERROR:src.common.cm3_logging:tis the error'
                          ])

    def test_log_with_logfile_generation(self):
        """Assert log generated contains the logged string in logger.

        Test if logfile generation happens with expected content in expected
        path and if log entries are in the expected format.
        """

        self.logger_obj.logger.info('info msg in logfile generation test')
        logger_name.warning('warning msg in logfile generation test')
        self.logger_obj.logger.error('error msg in logfile generation test')

        self.assertTrue(os.path.exists(self.expected_path),
                        msg=''.join([self.expected_path, ' does not exist']))

        # Using `with` to fix the linter warning: Consider using 'with' for
        # resource-allocating operations (consider-using-with)
        with open(self.expected_path, 'r', encoding='utf-8') as file_handle:
            # from the above file handle, we are checking entries of the form:
            # %(name)s - %(levelname)s - %(message)s')
            log_entry_to_grep = ('src.common.cm3_logging - ERROR - error'
                                 ' msg in logfile generation test')
            self.assertIn(log_entry_to_grep, file_handle.read())
            file_handle.seek(0)
            self.assertNotIn('scarborough fair', file_handle.read())


if __name__ == '__main__':
    absltest.main()
