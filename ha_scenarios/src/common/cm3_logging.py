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

"""Module for creating logger streams

There will be 2 logger streams:
* one streaming to console and
* the other to file (named <log_location>/<run_id>_runlog)
ex.: tests/testdata/1657669952_Jul1222_165232_runlog

The LoggerCls() class just needs to be initialized once from across the project
ideally in main() and then the values of all the following:
    print(f"self.logger = {self.logger}") # instance attr from inside class
    print(logger_obj.logger)  # the instance attribute from calling side
    print(logger_name)        # the module level attribute
point to the same object (referenced from across the project):
   self.logger = <Logger src.common.cm3_logging (INFO)>
   <Logger src.common.cm3_logging (INFO)>
   <Logger src.common.cm3_logging (INFO)>

Once the class LoggerCls() is instantiated anywhere in the project,
the module level variable logger_name acts as a global variable to refer
to a logger object that has 2 streams defined (as mentioned above):
    * c_handler = logging.StreamHandler(sys.stdout)
    * f_handler = logging.FileHandler(f_handler_filename)

The module level variable `logger_name` is referenced from other modules like
the oracle failure scenario modules by importing it like:
`from src.common.cm3_logging import logger_name`

"""
import logging
import pathlib
import sys
import datetime

logger_name = logging.getLogger(__name__)  # module level attribute
# this `logger_name` will be the same as instance attribute `self.logger` below


class LoggerCls():
    """LoggerCls defines the type logging.Logger with associated handlers.

    This class bundles the logger object with the handlers for
    console / file stream end the format desired for the log messages. Finally,
    adds them to the logger object """
    def __init__(self, run_id: str, log_location: str):
        self.run_id = run_id
        self.log_location = log_location
        self.logger = logger_name
        self.setup_logchannels()
        print(f'self.logger = {self.logger}')

    def setup_logchannels(self) -> None:
        """ Create 2 handlers : one for console and one for file logging.

        These handlers will be attached to the named logger we created above.
        """
        self.logger.setLevel(logging.INFO)
        # without this, individual handlers for logger only O/P WARNING & above

        self.setup_console_logchannel()
        self.setup_file_logchannel()

    def setup_console_logchannel(self) -> None:
        """Define handler and message format for console streaming logs"""
        c_handler = logging.StreamHandler(sys.stdout)

        # set the logging level for the console channel
        c_handler.setLevel(logging.INFO)

        # define the format of the log record for the console channel/handler
        c_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')

        # attach the above format to the respective handler
        c_handler.setFormatter(c_format)

        # attach the console handler to the named logger
        self.logger.addHandler(c_handler)

    def setup_file_logchannel(self) -> None:
        """Define handler and message format for console streaming logs"""
        f_handler_filename = str(pathlib.PurePath(self.log_location, ''.join(
            [self.run_id, '_runlog'])))
        f_handler = logging.FileHandler(f_handler_filename)

        # set the logging level for the file logging channel
        f_handler.setLevel(logging.INFO)

        # define the format of the log record for the file logging
        # channel/handler above
        f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s '
                                     '- %(message)s')

        # attach the above format to the respective handler
        f_handler.setFormatter(f_format)

        # attach the file logging handler to the named logger
        self.logger.addHandler(f_handler)


def logger_standalone_runner():
    """Code block to test this module independently as a script"""

    # pylint: disable=invalid-name
    # Naming consistent with other modules
    THIS_DIR = pathlib.Path(__file__).absolute().parent
    RUN_ID = datetime.datetime.now().strftime('%s_%b%d%y_%H%M%S')

    scenario = 'testing'
    # ex.: 1657669952_Jul1222_165232
    LOG_LOCATION = ''.join([str(THIS_DIR),'/../../logs/',RUN_ID, '_',scenario])
    pathlib.Path(LOG_LOCATION).mkdir(parents=True, exist_ok=True)

    logger_obj = LoggerCls(RUN_ID, LOG_LOCATION)

    # print out some test messages
    logger_obj.logger.info('info sir')
    logger_name.warning('This is a warning')
    logger_obj.logger.error('tis the error')


if __name__ == '__main__':
    logger_standalone_runner()
