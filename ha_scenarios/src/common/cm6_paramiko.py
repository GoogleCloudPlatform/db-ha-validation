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

"""Module to create Paramiko connection object to BMX DB backends

The ClientCls in this module has the following 3 methods that are called
from main() & other scenario() modules with the relevant parameters:
1) garbage_clean() => close the connection object and garbage clean
2) run_remote_cmd() => run cmd in ssh-ed host and return raw streams
3) store_op_to_py_variables() => run cmd in ssh-ed host & return processed o/p.
                                 This method helps to keep the code DRY.
"""

import json
import pathlib
from paramiko import SSHClient, RSAKey, AutoAddPolicy

THIS_DIR = pathlib.Path(__file__).absolute().parent # pylint: disable=invalid-name


class ClientCls:
    """ Provides paramiko client object to the caller and instance methods.

    Create an initial Paramiko client object and then use it inside
    the module for all remote connection operations on a particular host.

    The two exposed instance method facilities run cmds remotely returning both
    bstr & decoded output. These are needed for different usecases in different
    scenarios when they are introduced.

    An example invocation of the functionalities provided by this class may be
    as follows:

    host_ssh_clientobj = cm6_paramiko.ClientCls(host='172.16.30.1',
                                                username='ansible9',
                                                key_file='/home/.ssh/pvtkey')
    stdout_raw, stderr_raw = host_ssh_clientobj.run_remote_cmd('date')
    stdout_bstr, stderr_bstr = stdout_raw.read(), stderr_raw.read()
    output_hostname_cmd = host_ssh_clientobj.store_op_to_py_variables(hostname)
    host_ssh_clientobj.garbage_clean()
    """
    exec_timeout = 30

    def __init__(self, host, username, key_file, port=22):
        self.username = username
        self.key_file = key_file
        self.pkey = RSAKey.from_private_key_file(key_file)
        self.client = SSHClient()
        self.client.set_missing_host_key_policy(AutoAddPolicy())
        self.client.connect(host, port, username=username, pkey=self.pkey)

    def garbage_clean(self):
        """ Close the SSHClient object and remove the object """
        if self.client is not None:
            self.client.close()
            self.client = None

    def run_remote_cmd(self, command: str) -> tuple:
        """exec the cmd, return the raw stdout/stderr to the caller"""
        try:
            _, stdout, stderr = self.client.exec_command(
                command, timeout=self.exec_timeout)
        # exceptions for failing remote SSH commands will be varied
        # we want to catch and report any unexpected error to caller
        # pylint: disable-next=broad-except
        except Exception as inst:
            print(inst.args)
            exit(1)
        return stdout, stderr

    # Additional facility
    # function to run facts gathering commands and return decoded stdout
    def store_op_to_py_variables(self, command: str) -> str:
        """exec the cmd, return the utf-decoded text to the caller"""
        stdout, _ = self.run_remote_cmd(command)
        return stdout.read().decode()


# Following code is to do unit test of just this module independently
def paramiko_standalone_runner() -> None:
    """ standalone runner to run this module as a script independently """
    json_file = "".join([str(THIS_DIR), '/../../tests/testdata/site_constants'
                                        '.json'])

    with open(json_file, encoding="utf-8") as json_constants_fh:
        deserialized_data = json.load(json_constants_fh)

    # setup vars to be used in the standalone runner
    host_1_ip = deserialized_data["nodes"][0]["host_ip"]
    host_2_ip = deserialized_data["nodes"][1]["host_ip"]
    dict_nodes_logs_node1 = deserialized_data["nodes"][0]["dict_oracle_logs"]
    ssh_username = deserialized_data["ssh_user_name"]
    ssh_key = deserialized_data["ssh_key_file"]

    # cmd to be run against node 1
    cmd1_hw_markers_node1 = " ".join(
        ["sudo stat -c '%s' ", " ".join(sorted(dict_nodes_logs_node1.values()))])

    # cmd to be run against node 2
    # we just run a different arbitrary cmd in node2
    cmd1_hw_markers_node2 = "hostname; date"

    # Instantiate Client() and its method store_op_to_py_variables()
    host_1_ssh_clientobj = ClientCls(host=host_1_ip, username=ssh_username,
                                  key_file=ssh_key)
    op_cmd1_hw_markers_node1 = host_1_ssh_clientobj.store_op_to_py_variables(
        cmd1_hw_markers_node1)
    print(op_cmd1_hw_markers_node1)
    host_1_ssh_clientobj.garbage_clean()

    # call the method run_remote_cmd()
    host_2_ssh_clientobj = ClientCls(host=host_2_ip, username=ssh_username,
                                  key_file=ssh_key)
    stdout, stderr = host_2_ssh_clientobj.run_remote_cmd(cmd1_hw_markers_node2)
    # print(stdout, '########\n', stderr, '########\n')
    print(stdout.read(), '########\n', stderr.read(), '########\n')

    host_2_ssh_clientobj.garbage_clean()


if __name__ == '__main__':
    paramiko_standalone_runner()
