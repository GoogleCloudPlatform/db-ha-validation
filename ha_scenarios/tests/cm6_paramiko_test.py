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

"""Tests for paramiko module that runs commands in remote BMX DB backends

Details on each test is attempted to be documented in test function or in-line.
Erring on the side of too-much-documentation for my own recollection later :)

"""
import pathlib
import sys
import json
import unittest
from unittest.mock import patch, Mock
from absl.testing import absltest

import paramiko

THIS_DIR = pathlib.Path(__file__).absolute().parent  # pylint: disable=invalid-name
sys.path.append(str(THIS_DIR.parent))
# pylint: disable-next=import-error,wrong-import-position
from src.common.cm6_paramiko import ClientCls

# pylint: disable=unused-argument
# reason: mocked object `mocked_paramiko_sshclient` should be supplied as an
# arg into test* functions along with `self`

# pylint: disable=invalid-name
# ClientCls_obj follows class naming of code under test


class TestParamikoClient(absltest.TestCase):
    """Test attributes and methods of the object instantiated from ClientCls()

    The ClientCls_obj will be tested here with the details from a json file
    saved in the testdata for ssh_key_file & ssh_user_name used to connect to
    the remote host.

    """

    @classmethod
    def setUp(cls) -> None:
        super(TestParamikoClient, cls)  # go/gpylint-faq#g-missing-super-call
        cls.site_constants_json = "".join([str(THIS_DIR), '/testdata'
                                                          '/site_constants'
                                                          '.json'])
        with open(cls.site_constants_json, encoding="utf-8") \
                as json_constants_fh:
            deserialized_data = json.load(json_constants_fh)

        cls.host_1_ip = deserialized_data["nodes"][0]["host_ip"]
        cls.ssh_username = deserialized_data["ssh_user_name"]
        cls.ssh_key = deserialized_data["ssh_key_file"]

    @classmethod
    def tearDown(cls) -> None:
        # garbage collect the swingbench_obj instance after tests
        cls.ClientCls_obj = None
        super(TestParamikoClient, cls)  # go/gpylint-faq#g-missing-super-call

    @patch("src.common.cm6_paramiko.RSAKey", spec=True)
    @patch('src.common.cm6_paramiko.SSHClient', spec=True)
    def test_paramiko_client_obj_created_isinstance_of_paramiko_client(self,
                                                                       mocked_paramiko_sshclient,
                                                                       mocked_rsakey):
        """ Test if the ClientCls constructor calls paramiko pkg's SSHClient()

        Logic is as follows:
        1) @patch('src.common.cm6_paramiko.SSHClient', spec=True) creates a
        mock object named `mocked_paramiko_sshclient` (provided as arg to test)

        This is akin to:
        mocked_paramiko_client = Mock(spec=paramiko.SSHClient)

        `spec` ensures that you cannot mock any arbitrary method or attribute
        that is not present in the `paramiko.SSHClient` class.

        2) We don't patch the SSHClient where it's defined, but patch it where
        it is referenced in our module src/common/cm6_paramiko (doc reference:
        https://docs.python.org/3/library/unittest.mock.html#where-to-patch)
        namely: src.common.cm6_paramiko.SSHClient

        This means all calls to paramiko.SSHClient in src.common.cm6_paramiko
        initiated from this test module is intercepted by the mocked:
        `mocked_paramiko_sshclient`.

        3) The flow is:
            a) cm6_paramiko_test instantiates > ClientCls_obj of type:
            cm6_paramiko.ClientCls()
            b) Constructor of ClientCls() calls paramiko.SSHClient which is
            handled by the mocked_paramiko_sshclient
            c) self.client = SSHClient()  # ClientCls_obj.client is a SSHClient
            object & above assignment calls paramiko.SSHClient
            d) Since we are mocking SSHClient(), any operations on SSHClient()
             's methods are mocked, but the SSHClient() itself is of the spec's
             type: `paramiko.SSHClient` which we are asserting in this test

        4) The patch: @patch("src.common.cm6_paramiko.RSAKey", spec=True)
        is needed so that the constructor for ClientCls_obj successfully gets
        past the foll. even if the `ssh_key_file referenced in
        testdata/site_constant.json is not available in tester's environment:
        self.pkey = RSAKey.from_private_key_file(key_file)

        """
        ClientCls_obj = ClientCls(host=self.host_1_ip,
                                  username=self.ssh_username,
                                  key_file=self.ssh_key)

        self.assertTrue(isinstance(ClientCls_obj.client,
                                   paramiko.SSHClient))
        self.assertTrue(ClientCls_obj.client.connect.called)

        self.assertEqual(ClientCls_obj.client.connect.call_count, 1)

    @patch("src.common.cm6_paramiko.RSAKey", spec=True)
    @patch('src.common.cm6_paramiko.SSHClient', spec=True)
    def test_paramiko_client_obj_created_iscalled_withcorrect_args(self,
                                                                   mocked_paramiko_sshclient,
                                                                   mocked_rsakey):
        """ Test if ClientCls_obj instance makes the correct `connect` call

        We verify that the `connect` call using the SSH client object to the
        BMX host is done with the expected arguments.

        The expected arguments are the dict keys stores in the file:
        '/testdata/site_constants.json' for ssh_user_name & ssh_key_file.

        The mocked ClientCls_obj.client.connect.call_args will be something like:
        # call('172.16.110.1', 22, username='ansible9',
        # pkey=<paramiko.rsakey.RSAKey object at 0x7f33b3089eb0>)
        """
        ClientCls_obj = ClientCls(host=self.host_1_ip,
                                  username=self.ssh_username,
                                  key_file=self.ssh_key)


        self.assertEqual(ClientCls_obj.client.connect.call_args[0][0],
                         self.host_1_ip)

        self.assertEqual(ClientCls_obj.client.connect.call_args[0][1],
                         22)

        self.assertEqual(ClientCls_obj.client.connect.call_args[1]['username'],
                         self.ssh_username)

        # Due to the first decorator for RSAKey the pkey object is a MagicMock
        self.assertFalse(
            isinstance(ClientCls_obj.client.connect.call_args[1]['pkey'],
                       paramiko.rsakey.RSAKey))

        self.assertTrue(
            isinstance(ClientCls_obj.client.connect.call_args[1]['pkey'],
                       unittest.mock.MagicMock))

    @patch("src.common.cm6_paramiko.RSAKey", spec=True)
    @patch('src.common.cm6_paramiko.SSHClient', spec=True)
    def test_paramiko_client_obj_created_returns_mocked_bstr(self,
                                                             mocked_paramiko_sshclient,
                                                             mocked_rsakey):
        """ Test the values returned by Paramiko client's exec_command method.

        We are checking the returned values from the foll. 2 instance methods:
        run_remote_cmd() & store_op_to_py_variables()

        """

        ClientCls_obj = ClientCls(host=self.host_1_ip,
                                  username=self.ssh_username,
                                  key_file=self.ssh_key)
        mocked_stdin_channel = Mock(spec=paramiko.channel.ChannelStdinFile)
        mocked_stdout_channel = Mock(spec=paramiko.channel.ChannelFile)
        mocked_stderr_channel = Mock(spec=paramiko.channel.ChannelStderrFile)

        mocked_stdin_channel.read.return_value = b''
        mocked_stdout_channel.read.return_value = b'Lost But Won-Zimmer'
        mocked_stderr_channel.read.return_value = b'Leave No Man Behind-Zimmer'

        ClientCls_obj.client.exec_command.return_value = (
            mocked_stdin_channel, mocked_stdout_channel, mocked_stderr_channel)

        # we are testing run_remote_cmd() method
        # run_remote_cmd() returns raw Paramiko channel objects
        ret_val1, ret_val2 = ClientCls_obj.run_remote_cmd('date')
        self.assertTrue(isinstance(ret_val1, paramiko.channel.ChannelFile))
        self.assertEqual(ret_val1.read(), b'Lost But Won-Zimmer')
        self.assertEqual(ret_val2.read(), b'Leave No Man Behind-Zimmer')

        # we are testing store_op_to_py_variables() method
        # store_op_to_py_variables() returns utf-decoded value of bstr output
        ret_val3 = ClientCls_obj.store_op_to_py_variables("ls -l /etc ; date")
        self.assertEqual(ret_val3, 'Lost But Won-Zimmer')

    @patch("src.common.cm6_paramiko.RSAKey", spec=True)
    @patch('src.common.cm6_paramiko.SSHClient', spec=True)
    def test_paramiko_client_obj_created_has_timeout_correctly_set(self,
                                                                   mocked_paramiko_sshclient,
                                                                   mocked_rsakey):
        """ Test if Paramiko client object sends correct timeout in its payload

        For simplicity of testing code, following call is made with return
        value of a (tuple of ints) whereas actual call should use a (tuple
        of `paramiko.channel.ChannelFile`). Since we are testing a different
        aspect of the code under test, n5amely, the SSH timeout defined as a
        class variable, this should be fine.
        """

        ClientCls_obj = ClientCls(host=self.host_1_ip,
                                  username=self.ssh_username,
                                  key_file=self.ssh_key)

        ClientCls_obj.client.exec_command.return_value = (1000, 2000, 3000)
        ClientCls_obj.run_remote_cmd("really_slow_command")
        self.assertEqual(ClientCls_obj.client.exec_command.call_args[1]['timeout'],
                         ClientCls_obj.exec_timeout)

    @patch("src.common.cm6_paramiko.RSAKey", spec=True)
    @patch('src.common.cm6_paramiko.SSHClient', spec=True)
    def test_paramiko_client_obj_created_is_closed(self,
                                                   mocked_paramiko_sshclient,
                                                   mocked_rsakey):
        """ Test is the Paramiko client object is cleanly closed.

        This is to ensure that all remote commands are intentional and no stray
        command executions happen via a left-over Paramiko client object.

               From docstring for `class SSHClient`:
     |      .. warning::
     |          Paramiko registers garbage collection hooks that will try to
     |          automatically close connections for you, but this is not presently
     |          reliable. Failure to explicitly close your client after use may
     |          lead to end-of-process hangs!
        """
        ClientCls_obj = ClientCls(host=self.host_1_ip,
                                  username=self.ssh_username,
                                  key_file=self.ssh_key)

        # assert that SSHClient.close() is not yet called
        self.assertTrue(ClientCls_obj.client.close.not_called)

        # Now triggering the client close
        ClientCls_obj.garbage_clean()

        # we cannot do the following assertion:
        # `self.assertTrue(ClientCls_obj.client.close.called)`
        # because the SSH client object `ClientCls_obj.client` itself is
        # garbage collected by the `garbage_clean()` method

        # we will get the following error if we were to issue the above assert:
        # AttributeError: 'NoneType' object has no attribute 'close'
        # as the ClientCls_obj.client is cleaned from the namespace

        # we use the following assertions instead
        self.assertEqual(ClientCls_obj.client, None)
        self.assertFalse(ClientCls_obj.client)


if __name__ == '__main__':
    absltest.main()
