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

"""Module to start Swingbench workload controlled by parameters from caller

Swingbench is kicked off locally from inside the control node itself from where
tns connection is established to the BMX DB hosts scan name.
`run_id` and `log_location` controls where the output files get written to.
"""

from subprocess import Popen
import itertools
import pathlib
import time
import sys
import datetime
import json

THIS_DIR = pathlib.Path(__file__).absolute().parent
sys.path.append(str(THIS_DIR.parent.parent))  # current directory structure is:
# <root> > src > common > <common module like the current  one>
from src.common import cm1_json_file_flag


class Swingbench:
    """ Processes Swingbench related keys in input & provides methods to act on it.

    Following methods  are exposed that provide Swingbench related
    functionality:
    (1) generate_swingbench_tokens => constructs tokens to subprocess.Popen()
    (2) run_swingbench => runs the Swingbench binary in the background as a
    non-blocking call
    """

    def __init__(self, rt_hhmm: str, run_id: str, log_location: str) -> None:
        self.rt_hhmm = rt_hhmm
        self.run_id = run_id
        self.log_location = log_location

        self.swingbench_binary = [cm1_json_file_flag.deserialized_data[
            "swingbench_binary_location"]]
        self.swingbench_config_file = cm1_json_file_flag.deserialized_data[
            "swingbench_config_file"]

    def generate_swingbench_tokens(self) -> list:
        """ This method parses the input json file to generate tokens.

        subprocess.Popen expects its args as individual tokens.
        Example: Foll. will error
            subprocess.Popen(["/usr/bin/echo helloworld"])

        while this will not as it has the list / tokens correctly fed to Popen:
        subprocess.Popen(["/usr/bin/echo" , "helloworld"])

        An example of the generated tokens is as follows:
        ['/home/user/swingbench/swingbench/bin/charbench', '-c',
        '/home/user/swingbench/swingbench/configs
        /soepdb_ac_highertimeouts.xml', '-r',
        '/home/user/tests/testdata/logs/1671483924_Dec1922_130524.xml',
        '-rt', '00:02', '-a', '-v', '-nc']
        """

        # Ex.: sb_option_config_file =['-c',
        # '/home/swingbench/configs/1672193927_Dec2722_181847.xml']
        sb_option_config_file = ['-c', self.swingbench_config_file]

        # ex.: sb_option_results_xml = ['-r',
        # '/home/swingbench/bin/1672193927_Dec2722_181847.xml']
        sb_results_xml_filename = pathlib.PurePath(self.log_location,
                                                   "".join([self.run_id, ".xml"
                                                            ])).as_posix()

        sb_option_results_xml = ['-r', sb_results_xml_filename]

        # Ex.: swingbench_runtime = "-rt 0:30"
        # swingbench runtime differs based on scenario being tested
        sb_option_runtime = ['-rt', self.rt_hhmm]

        sb_option_all = ['-a']
        sb_option_verbose = ['-v']
        sb_option_noclobber = ['-nc']

        swingbench_cmd_tokens = itertools.chain(
            self.swingbench_binary,
            sb_option_config_file,
            sb_option_results_xml,
            sb_option_runtime,
            sb_option_all,
            sb_option_verbose,
            sb_option_noclobber
        )

        return list(swingbench_cmd_tokens)

    def run_swingbench(self, swingbench_cmd_tokens) -> None:
        """ Method that starts swingbench workload.

        Swingbench is started from the control-node with the runtime swingbench
        argument based on scenario and other swingbench arguments based on the
        config values in json file """

        sb_runlog = pathlib.PurePath(self.log_location, "".join(
            [self.run_id, "_swingbench_timeseries"])).as_posix()

        # Calling sp.run() is a blocking call
        # while sp.Popen is not
        # Using Popen to run the swingbench in background
        with open(sb_runlog, "a", encoding="utf-8") as file_handle:
            Popen(swingbench_cmd_tokens, stdout=file_handle)

        # Sleep for 90secs until the Swingbench load is ramped to full TPS.
        # Note that this doesn't change anything in the xml parser logic,
        # as we are still going to get 0s at the beginning of the xml file

        # We do blocking call here so that when scenarios are introduced by
        # main() module, failovers are triggered only after full ramp up of the
        # Swingbench workload.
        print('Waiting 90 seconds for SwingBench to ramp up')
        time.sleep(90)


def swingbench_standalone_runner() -> None:
    """ standalone runner to run this module as a script independently """

    json_file = "".join([str(THIS_DIR), '/../../tests/testdata/site_constants'
                                        '.json'])

    with open(json_file, encoding="utf-8") as json_constants_fh:
        deserialized_data = json.load(json_constants_fh)

    cm1_json_file_flag.deserialized_data = deserialized_data

    run_id = datetime.datetime.now().strftime('%s_%b%d%y_%H%M%S')
    log_location = THIS_DIR / '../../logs'

    sb_runtime = '00:02'
    swingbench_obj = Swingbench(sb_runtime, run_id, log_location)
    swingbench_cmd_tokens = swingbench_obj.generate_swingbench_tokens()
    print(swingbench_cmd_tokens)
    swingbench_obj.run_swingbench(swingbench_cmd_tokens)


if __name__ == '__main__':
    swingbench_standalone_runner()
