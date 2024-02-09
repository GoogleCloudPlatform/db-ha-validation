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

"""Extract snippets from Oracle log files for the duration of failure scenario

The log files excerpted are: Oracle ASM, Oracle CRS & Oracle RDBMS alert logs.

After each scenario run, the o/p directory should contain files that start
with a run id (a unique string) like `1656981757_jul0422_174328` and the foll.
local files each of which is excerpted from a counterpart alertlog housed in
the remote DB RAC hosts:

1656981757_jul0422_174328_node1.asm_log => ASM log from node1
1656981757_jul0422_174328_node1_crs_log => CRS log from node1
1656981757_jul0422_174328_node1_db_log => RDBMS alert log from node1
1656981757_jul0422_174328_node2.asm_log  => ASM log from node2
1656981757_jul0422_174328_node2_crs_log  => CRS log from node2
1656981757_jul0422_174328_node2_db_log => RDBMS alert log from node2

The above will be in addition to the following 2:
1656981757_jul0422_174328_results.xml,
1656981757_jul0422_174328_runlog,
... which will be generated by the swingbench() and main() modules.


"""
import pathlib
import sys
import datetime
import json
import itertools

THIS_DIR = pathlib.Path(__file__).absolute().parent
sys.path.append(str(THIS_DIR.parent.parent))

# reason for the foll. pylinter exception is: project directory structure is:
# <root> > src > common > <common modules like the current one>
# to import module from non-standard path, the following import needs to be
# placed after the sys.path is appended as above

# pylint: disable-next=import-error,wrong-import-position
from src.common import cm6_paramiko, cm1_json_file_flag


class ExcerptorCls:
    """Provides methods to: 1) record HWMs & 2) after failover excerpt content.

    ExcerptorCls has a method generate_get_hwm_groupby_host() to generate
    high watermarks and another excerpt_logs() to use the geenrated HWMs and
    then extract just the changed lines.

    The generate_get_hwm_groupby_host() will be invoked prior to triggering a
    given failure scenario. Once the scenario has caused the outage that is
    intended, the excerpt_logs() method will be called from the control-node/VM
    to pull the remote Oracle logs in the BMX db backend hosts to the local
    control-node's location where all logs will be generated for a given run of
    a failure scenario.
    """

    def __init__(self, run_id: str, log_location: str):
        self.run_id = run_id
        self.log_location = log_location
        self.tail_cmds_dict = {}
        self.ssh_username = cm1_json_file_flag.deserialized_data["ssh_user_name"]
        self.ssh_key = cm1_json_file_flag.deserialized_data["ssh_key_file"]
        self.deserialized_data = cm1_json_file_flag.deserialized_data

    def generate_get_hwm_groupby_host(self):
        """Record high watermarks of all alert logs in all DB backend hosts.

        The input site-constants.json contains all the Oracle log files that
        are of immediate interest to understand what happened during a given
        failure scenario simulation. The json file will be consulted to
        remotely reach via SSH into the remote nodes and record the high
        watermarks for each of the logfile of interest.

        The high watermarks generated will be held in a dict data structure of
        a list of tuples that is grouped/keyed by the hostname. Ex.:
        {
          '172.16.110.1': [
            ('/u01/app/diag/asm/+asm/+ASM1/trace/alert_+ASM1.log', '16699'),
            ('/u01/app/diag/crs/at--svr005/crs/trace/alert.log', '217206'),
            ('/u01/app/diag/rdbms/orcl/orcl1/trace/alert_orcl1.log', '74373')
          ],
          '172.16.110.2': [
            ('/u01/app/diag/asm/+asm/+ASM2/trace/alert_+ASM2.log', '27358'),
            ('/u01/app/diag/crs/at--svr006/crs/trace/alert.log', '3907'),
            ('/u01/app/diag/rdbms/orcl/orcl2/trace/alert_orcl2.log', '86297')
          ]
        }

        Erring on the side of over-documentation, the code below may have an
        occasional variable expansion provided for ease of review process,
        which shall be removed before publishing.
        """

        for _, dict_node_details in enumerate(
                self.deserialized_data["nodes"]):

            # Ex.:
            # _ = 0 (the node number in the json file's dict)

            # dict_node_details =  {
            # 'node_name': 'at-3793329-svr005',
            # 'host_ip': '172.16.110.1',
            # 'dict_oracle_logs': {
            #   'node1_asm_log': '/u01/app//+asm/+ASM1/trace/alert_+ASM1.log',
            #   'node1_crs_log': '/u01/crs/at--svr005/crs/trace/alert.log',
            #   'node1_db_log': '/u01/app/orcl/orcl1/trc/alert_orcl1.log'}
            # }

            host_ip = dict_node_details['host_ip']
            dict_nodes_logs_node = dict_node_details['dict_oracle_logs']

            _cmd_hw_markers_wc = ['sudo /bin/wc -l']
            _cmd_hw_markers_log = list(dict_nodes_logs_node.values())

            cmd_hw_markers = " ".join(list(itertools.chain(
                _cmd_hw_markers_wc,
                _cmd_hw_markers_log
            )))

            # Ex.: cmd_hw_markers =
            # sudo /bin/wc -l  /u01/app/asm/+asm/+ASM1/trace/alert_+ASM1.log
            # /u01/crs/at-3793329-svr005/crs/trace/alert.log
            # /u01/app/oracle/orcl/orcl1/trc/alert_orcl1.log

            # Instantiate paramiko client object and get the high watermarks
            # of ASM, CRS, RDBMS alert logs via remote SSH commands
            host_ssh_clientobj = cm6_paramiko.ClientCls(host=host_ip,
                                                        username=self.ssh_username,
                                                        key_file=self.ssh_key)
            op_cmd_hw_markers = host_ssh_clientobj.store_op_to_py_variables(
                cmd_hw_markers)

            # Ex.: op_cmd_hw_markers
            #  27358 /u01/app/oracle/diag/asm/+asm/+ASM2/trace/alert_+ASM2.log
            #   3907 /u01/app/oracle/diag/crs/at--svr006/crs/trace/alert.log
            #  86297 /u01/app/oracle/rdbms/orcl/orcl2/trace/alert_orcl2.log
            # 117562 total

            host_ssh_clientobj.garbage_clean()

            # convert op_cmd1_hw_markers from str to list, splitting on \n
            op_cmd_hw_markers = op_cmd_hw_markers.split('\n')[
                                :-2]

            # Ex. op_cmd_hw_markers=
            # ['  27358 /u01/app/oracle//asm/+asm/+ASM2/trace/alert_+ASM2.log',
            # '   3907 /u01/app/oracle/diag/crs/at-/crs/trace/alert.log',
            # '  86297 /u01/app//diag/rdbms/orcl/orcl2/trace/alert_orcl2.log']

            tail_cmds_node = []
            for line in op_cmd_hw_markers:
                hwm_filename_list = line.split()
                # split on whitespace:
                # ['12058', '/u01/diag/asm/+asm/+ASM2/trace/alert_+ASM2.log']

                # append as a tuple
                tail_cmds_node.append((hwm_filename_list[1],
                                       hwm_filename_list[0]))

            self.tail_cmds_dict[host_ip] = tail_cmds_node

    def excerpt_logs(self) -> None:
        """Excerpt the remote files from BMX DB backend hosts onto local files.

        The remote log file locations & high watermarks are as per
        tail_cmds_dict.

        stdout from the remote SSH command execution will nbe written into
        local files in the control node from where the failover scenarios are
        simulated.

        The local file location in the control-node is a function of:
        run_id & log_location

        For ex.: output from:
        'sudo tail -n +16699 /u01/diag/+asm/+ASM1/trace/alert_+ASM1.log'
        will be written to: <log_location>/<run_id>_node1_asm_log

        The user-friendly local file name is `node1_asm_log` for
        `alert_+ASM1.log` as input in the `site_constants.json` file.
        """

        for node_number, dict_node_details in enumerate(
                self.deserialized_data["nodes"]):

            host_ip = dict_node_details['host_ip']
            dict_nodes_logs_node = dict_node_details['dict_oracle_logs']

            host_ssh_clientobj = cm6_paramiko.ClientCls(host=host_ip,
                                                        username=self.ssh_username,
                                                        key_file=self.ssh_key)

            for log_hwm_tuple in self.tail_cmds_dict[host_ip]:
                # use dict comprehension to match the absolute filename with
                # local filename like node2_asm_log
                local_filename = [k for k, v in dict_nodes_logs_node.items() if
                                  v == log_hwm_tuple[0]][0]

                op_file_nm = str(
                    pathlib.PurePath(self.log_location,
                                     "_".join([self.run_id, local_filename])))

                command = "".join(["sudo tail -n +", log_hwm_tuple[1], " ",
                                   log_hwm_tuple[0]])

                stdout_raw, stderr_raw = host_ssh_clientobj.run_remote_cmd(
                    command)
                stdout_bstr, _ = stdout_raw.read(), stderr_raw.read()

                with open(op_file_nm, "a", encoding='utf-8') as file:
                    file.write(stdout_bstr.decode())

            # close the client
            host_ssh_clientobj.garbage_clean()


def excerptor_standalone_runner():
    """Run this module independently as a script"""
    json_file = "".join([str(THIS_DIR), '/../../tests/testdata/site_constants'
                                        '.json'])

    with open(json_file, encoding="utf-8") as json_constants_fh:
        deserialized_data = json.load(json_constants_fh)

    cm1_json_file_flag.deserialized_data = deserialized_data

    run_id = datetime.datetime.now().strftime('%s_%b%d%y_%H%M%S')
    log_location = THIS_DIR / '../../logs'

    # Excerpt the logs generated for the duration of test
    excerptor_inst = ExcerptorCls(run_id, log_location)
    excerptor_inst.generate_get_hwm_groupby_host()
    # excerptor_inst.excerpt_logs()


if __name__ == '__main__':
    excerptor_standalone_runner()
