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

"""Module that acts as entrypoint for command line invocation."""
import datetime
import time
import pathlib
from absl import app, flags
from src.common import cm1_json_file_flag
from src.common.cm2_parse_resultsxml import ParseSwingbenchRunXML
from src.common.cm3_logging import LoggerCls
from src.common import cm4_tailing_cls
from src.common.cm5_setup_swingbench_return_sbtokens import Swingbench
from src.common.cm6_paramiko import ClientCls

# the dict _RUNTIME_SCENARIO_DICT is based on prior benchmarking runs at:
# go/bmx-oracle-rac:failover-benchmarks
_RUNTIME_SCENARIO_DICT = {'testing': '00:02', 'kernel_panic': '00:20',
                          'shutdown': '00:20', 'reset_api': '00:20',
                          'hba_asm_lun': '00:30', 'hba_root_lun': '00:30',
                          'hba_all_ports_down': '03:30',
                          'oracleinst_down': '00:02',
                          'listener_crash': '00:03'}

scenario_names = list(_RUNTIME_SCENARIO_DICT.keys())

_JSON_FILE = flags.DEFINE_string(
    'json_file',
    None,
    'Json file containing site-specific constants',
    short_name='j',
    required=True,
)

_SCENARIO = flags.DEFINE_enum(
    'scenario',
    default=None,
    enum_values=scenario_names,
    help=''.join(
        ['Scenario to choose from choices of: ', ', '.join(scenario_names)]
    ),
    short_name='s',
    required=True,
)

_NODE_IP_TO_TEST = flags.DEFINE_string(
    'node_ip_to_test',
    default=None,
    help=(
        'The node where fault injection is desired, '
        'default is node number two in the input json file'
    ),
    short_name='n',
)

_LOG_DEST = flags.DEFINE_string(
    'log_dest',
    default='.',
    help=(
        'OS directory where logs will be created for this scenario run,'
        'default is `pwd`'
    ),
    short_name='l',
)

run_id = datetime.datetime.now().strftime(
    '%s_%b%d%y_%H%M%S')  # ex.: 1657669952_Jul1222_165232

# Constants used universally across by all modules
LOG_LOCATION = None
NODE_TO_TEST = None


def _scenario_testing() -> None:
    """ Sample placeholder function.

    All scenarios in _RUNTIME_SCENARIO_DICT will have a function like this
    to process a given scenario """

    # processing logic for a given failure scenario will be offloaded to its
    # own module as follows
    from src.scenarios import \
        sm0_testing  # pylint: disable=import-outside-toplevel
    sm0_testing.do_something()


def _scenario_oracleinst_down(node_ip_to_test: str):
    from src.scenarios import sm1_instancedown
    cmds_kill_oracleinst_down = sm1_instancedown.cmds_scenario_oracleinst_down()
    sm1_instancedown.run_scenario_oracleinst_down(
        cmds_kill_oracleinst_down, node_ip_to_test)


# process input flags and do tasks based on the values received
def process_input_flags():
    """ Process input parameters and populate deserialized_data

    Actions performed by this function:
    1) hydrate project-wide variable cm1_json_file_flag.deserialized_data
    from input json file
    2) process input variables and set values for log_location, run_id"""

    # process _JSON_FILE (FLAGS.json_file)
    deserialized_data = cm1_json_file_flag.deserialize_json()

    # process _LOG_DEST (FLAGS.log_dest)
    # into global scope that's referred in multiple functions/modules from main
    global LOG_LOCATION  # pylint: disable=global-statement
    LOG_LOCATION = pathlib.Path(_LOG_DEST.value, "".join(
        [run_id, "_", _SCENARIO.value])).resolve()
    # Logger will create the LOG_LOCATION & this's redundant, but leaving it
    # here for now for testing of log_dest flag
    pathlib.Path(LOG_LOCATION).mkdir(parents=True, exist_ok=True)

    # process _NODE_IP_TO_TEST (FLAGS.node_ip_to_test)
    # into global scope that's referred in multiple functions/modules from main
    if _NODE_IP_TO_TEST.value is None:
        global NODE_TO_TEST  # pylint: disable=global-statement
        NODE_TO_TEST = deserialized_data["nodes"][1]["host_ip"]


def main(argv) -> None:
    """ Entry point to all the modules"""
    del argv

    process_input_flags()

    # ### Create log location & Initialize logger
    # log location is of the form: <log_dest>/<RUN_ID>_<scenario>
    # Ex.: <log_dest>/1657669952_Jul1222_165232_oracleinst_down
    LOG_LOCATION = pathlib.Path(_LOG_DEST.value, "".join(
        [run_id, "_", _SCENARIO.value])).resolve()
    # pathlib.Path(LOG_LOCATION).mkdir(parents=True, exist_ok=True)

    logger_obj = LoggerCls(run_id, LOG_LOCATION)
    logger_obj.logger.info(f'Values received from command line for this run '
                           f'is: {flags.FLAGS.flag_values_dict()}')

    deserialized_data = cm1_json_file_flag.deserialized_data
    logger_obj.logger.debug(f'deserialized_data in main: {deserialized_data}')

    # ### Swingbench processing
    sb_runtime = _RUNTIME_SCENARIO_DICT[_SCENARIO.value]
    logger_obj.logger.debug(
        f"Swingbench runtime: {sb_runtime} for scenario: {_SCENARIO.value}")
    swingbench_obj = Swingbench(sb_runtime, run_id, LOG_LOCATION)
    swingbench_cmd_tokens = swingbench_obj.generate_swingbench_tokens()
    swingbench_obj.run_swingbench(swingbench_cmd_tokens)

    logger_obj.logger.info(
        f'The Swingbench cmd tokens are: {swingbench_cmd_tokens}')

    # Record high watermarks of ASM, CRS, RDBMS alert logs in both RAC nodes
    excerptor_inst = cm4_tailing_cls.ExcerptorCls(run_id, LOG_LOCATION)
    # tail_cmds_nodeee2 = generate_get_hwm_cmds_for_given_host(1)
    excerptor_inst.generate_get_hwm_groupby_host()

    # send hwms to logger
    logger_obj.logger.info(
        f'The high watermarks of the logs are:{excerptor_inst.tail_cmds_dict}')

    # connect to BMX backend hosts and run failure scenario commands
    # This is the traffic director in main()
    if _SCENARIO.value == 'testing':
        _scenario_testing()
    elif _SCENARIO.value == 'oracleinst_down':
        _scenario_oracleinst_down(NODE_TO_TEST)

    # Parse the swingbench results xml to deduce the failover latency
    sb_results_xml_filename = str(
        pathlib.PurePath(LOG_LOCATION, "".join([run_id, ".xml"])))

    hh, mm = sb_runtime.split(':')
    sb_runtime_secs = int(hh) * 3600 + int(mm) * 60

    # We add 60s to Swingbench runtime to avoid the error:
    # FileNotFoundError: [Errno 2] No such file or directory:
    # '/home/jcnarasimhan/PycharmProjects/hadr/logs/1657844727_Jul1422_172527.xml'
    sb_blocking_time = sb_runtime_secs + 60
    logger_obj.logger.info(f'We are now going to sleep for {sb_blocking_time}')

    time.sleep(sb_blocking_time)

    # parse the generated xml file from the swingbench run
    # common_mod_01_parse_resultsxml.parse_swingbench_resultsxml(sb_results_xml_filename)
    parse_swingbench_run = ParseSwingbenchRunXML(sb_results_xml_filename)
    parse_swingbench_run.parse_swingbench_resultsxml()

    # Get the logs generated for the duration of test
    excerptor_inst.excerpt_logs()


if __name__ == '__main__':
    app.run(main)
