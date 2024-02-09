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

from src.common import cm1_json_file_flag, cm2_parse_resultsxml, \
    cm6_paramiko
from src.common.cm1_json_file_flag import deserialized_data

from src.common.cm3_logging import logger_name
logger_name.info(f'The fault injection is: terminate the Oracle instance via killing a background process')


def cmds_scenario_oracleinst_down() -> list:
    return [
        "echo PMON processes before instance shutdown",
        "date +%s ; date; ps -ef|grep pmon|grep -v grep",
        "date +%s ; date; ps -ef|grep pmon|grep -v grep|grep -v grid|awk '{print $2}'|sudo xargs kill -9; date +%s ; date",
        "echo PMON processes after instance shutdown"
        "date +%s ; date; ps -ef|grep pmon|grep -v grep"
    ]


def run_scenario_oracleinst_down(cmds_list_oracleinst_down: list, node_ip_to_test: str) -> list:
    ssh_username = deserialized_data["ssh_user_name"]
    ssh_key = deserialized_data["ssh_key_file"]
    host_ssh_clientobj = cm6_paramiko.ClientCls(host=node_ip_to_test, username=ssh_username,
                                                                        key_file=ssh_key)

    # initialize a list of tuples to hold stdout and stderr from each command executed
    stdout_stderr = []  # not going to work, as we need the asctime stamp immediately... storing in list to unpack
    # later not going to get the timestamp

    for command in cmds_list_oracleinst_down:
        logger_name.debug("\n", "#" * 20, "Running command:", command, )
        stdout_raw, stderr_raw = host_ssh_clientobj.run_remote_cmd(command)
        stdout_stderr.append((stdout_raw, stderr_raw))  # to be removed
        logger_name.debug("stdout: ", stdout_raw.read().decode())  # debug
        logger_name.debug("stderr: ", stderr_raw.read().decode())  # debug
        stdout_bstr, stderr_bstr = stdout_raw.read(), stderr_raw.read()
        logger_name.debug(stdout_bstr)
        logger_name.debug(stderr_bstr)

        if stdout_bstr:
            logger_name.info(f'stdout of shutdown command run is {stdout_bstr}')

        if stderr_bstr:
            logger_name.info(f'stderr of shutdown command run is {stderr_bstr}')

    host_ssh_clientobj.garbage_clean()
    return stdout_stderr

