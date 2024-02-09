# Simulating Failure Scenarios For Oracle RAC Workloads

The utilities presented with this GitHub repository will help to simulate various failure scenarios on a Oracle Real Application Cluster (RAC) configuration and to observe the dip in throughput as seen from an Oracle workload's standpoint before, during and after a failure scenario.

***Note:***
The steps detailed herein have been tested on a [Google Cloud Bare Metal Server](https://cloud.google.com/bare-metal) and assume that you have BMS hardware with no Oracle RAC installed yet. If you already have an existing RAC configuration, you can skip to section ["1a) Configuring 19c RAC Application Continuity"](#1a-configuring-19c-rac-application-continuity)


# Table of Contents

- [Objective](#objective)
- [How to use this repository - the tl;dr version](#how-to-use-this-repository-the-tldr-version)
- [How to use this repository - the detailed version](#how-to-use-this-repository-the-detailed-version)
	- [1) Perform pre-req: Create an Oracle RAC cluster](#1-perform-pre-req-create-an-oracle-rac-cluster)
		- [1a) Configuring 19c RAC Application Continuity](#1a-configuring-19c-rac-application-continuity)
	- [2) Perform pre-req: Download/Configure Swingbench](#2-perform-pre-req-downloadconfigure-swingbench)
	- [3) Perform pre-req: Install necessary Python packages in your control-node](#3-perform-pre-req-install-necessary-python-packages-in-your-control-node)
	- [4) Clone this repo to your local directory in control-node](#4-clone-this-repo-to-your-local-directory-in-control-node)
	- [5) Details: Kick off HA testing scenarios from command line:](#5-details-kick-off-ha-testing-scenarios-from-command-line)


# How to use this repository - the tl;dr version

Perform a Git clone of the code here to point at your own RAC cluster and simulate HA failover scenarios:

1) Pre-req: Create a RAC cluster and configure it to be ready to receive the Swingbench workload
  * Create a RAC DB service that is configured with `Application Continuity`

2) Pre-req: Download Swingbench and edit the config file to point Swingbench to your RAC cluster's service configured with application continuity

3) Pre-req: Install necessary Python packages in control-node

4) Clone this repo to your local directory in control-node so the developed code can be pointed at a RAC cluster and desired failover scenarios simulated

5) Kick off HA testing scenarios from command line. The script will
  * Trigger a Swingbench workload
  * Inject the desired fault into that RAC host where failure simulation is desired
  * Capture snippets from both the RAC hosts for the duration of the failure simulation
  * Parse the Swingbench results.xml data to calculate failover latency

# How to use this repository - the detailed version

The following schematic provides a high-level picture of the various components involved in the setup:

![hadr_automation_code_setup](https://github.com/google/bms-toolkit/assets/12689962/7f458223-e15c-4ba4-aef0-0f48cd511930)

All the steps like installing a RAC cluster on a BMX host infrastructure, installing/configuring the SwingBench tool on control node / jumphost, cloning this repo to the control host and simulating the various scenarios are detailed in the following sections.

## 1) Perform pre-req: Create an Oracle RAC cluster

1) Set up a control-node from where the installs/scenario tests will be run. We recommend using the OS image:`Debian GNU/Linux 11 (bullseye)"` for the GCP VM. The details of setting up connection or setting up jumphost/control-node are not detailed here, but can be found in the [bms docs](https://cloud.google.com/bare-metal/docs/bms-setup#bms-create-jump-host).

2) Clone the latest version of [bms-toolkit](https://github.com/google/bms-toolkit) into the client machine.
```
sudo apt update
sudo apt upgrade
sudo apt install git
git --version
```

 The client machine can be either the same control-node/jumphost that was set up in step 1 or it could be a host from where it is possible to ssh into the control-node:
```commandline
user@jon2:~/mydrive/bmaas/host_provisioning$ git clone https://github.com/google/bms-toolkit.git
Cloning into 'bms-toolkit'...
remote: Enumerating objects: 3059, done.
remote: Counting objects: 100% (3058/3058), done.
remote: Compressing objects: 100% (1451/1451), done.
remote: Total 3059 (delta 1489), reused 2812 (delta 1323), pack-reused 1
Receiving objects: 100% (3059/3059), 1.06 MiB | 3.89 MiB/s, done.
Resolving deltas: 100% (1489/1489), done.
```
3) The host-provisioning utility of the bms-toolkit can be called as below (repeat for each of the RAC cluster nodes) :
```commandline
✔ ~/mydrive/bmaas/host_provisioning/bms-toolkit [host-provision ↓·3|✚ 2…8]
22:12 $ ./host-provision.sh --instance-ip-addr 172.16.110.2  --instance-ssh-user ansible9 --proxy-setup true --u01-lun /dev/mapper/3600a098038314344372b4f75392d3850
```
  * The above example invocation has the following meaning:
     * `--instance-ip-addr  172.16.110.2` is one of the cluster nodes
     * `--instance-ssh-user ansible9` is OS username to be created on BMS host; user equivalence established for that user between BMX host & control node/VM
    * `--proxy-setup false` is to answer the questions: "Do you want to configure internet access on the BMS host"
    * `--u01-lun /dev/mapper/3600a098038314344372b4f75392d3850` is the block device that will manifest as `/dev/mapper/db-sw` which can be fed later into data mounts json file

***NOTE:*** Above host provisioning steps need to be done on each node that forms the Oracle RAC cluster.

4) Install 19c RAC database after adjusting the json files content (sample shown below) that is input to the `install-oracle.sh` utility:
```commandline

✔ ~/050521-mntrl-instlln/bms-toolkit [host-provision ↓·11|✚ 3…19] 
07:00 $ cat mntrl_asm.json
[{
  "diskgroup": "DATA",
  "disks": [
    { "name": "DATA_3161313547", "blk_device": "/dev/mapper/3600a09803831444a685d513161313547" },
    { "name": "DATA_316131354C", "blk_device": "/dev/mapper/3600a09803831444a685d51316131354c" },
    { "name": "DATA_3161313466", "blk_device": "/dev/mapper/3600a09803831444a685d513161313466" },
    { "name": "DATA_316131346B", "blk_device": "/dev/mapper/3600a09803831444a685d51316131346b" },
  ]},
 {
  "diskgroup": "RECO",
  "disks": [
    { "name": "RECO_316131354F", "blk_device": "/dev/mapper/3600a09803831444a685d51316131354f" },
    { "name": "RECO_3161313478", "blk_device": "/dev/mapper/3600a09803831444a685d513161313478" },
  ]}
]

✔ ~/050521-mntrl-instlln/bms-toolkit [host-provision ↓·11|✚ 3…19] 
07:00 $ cat mntrl_data_mounts_config.json
[
  {
    "purpose": "software",
    "blk_device": "/dev/udev-u01-mount-device",
    "name": "u01",
    "fstype":"xfs",
    "mount_point":"/u01",
    "mount_opts":"defaults"
  }
]

✔ ~/050521-mntrl-instlln/bms-toolkit [host-provision ↓·11|✚ 3…19] 
07:01 $ cat mntrl_cluster.json 
[
  {
    "scan_name": "mntrlscan",
    "scan_port": "1521",
    "cluster_name": "mntrl-2node-cluster",
    "cluster_domain": "company.brisbane.com",
    "public_net": "bond0.105",
    "private_net": "bond1.106",
    "scan_ip1": "172.16.110.20",
    "scan_ip2": "172.16.110.21",
    "scan_ip3": "172.16.110.22",
    "dg_name": "DATA",
    "nodes": [
      {  "node_name": "at-3793329-svr005",
         "host_ip": "172.16.110.1",
         "vip_name": "at-3793329-svr005-vip",
         "vip_ip": "172.16.110.11"
      },
      {  "node_name": "at-3793329-svr006",
         "host_ip": "172.16.110.2",
         "vip_name": "at-3793329-svr006-vip",
         "vip_ip": "172.16.110.12"
      }
    ]
  }
]


✔ ~/050521-mntrl-instlln/bms-toolkit [host-provision ↓·11|✚ 3…19]
13:12 $ nohup ./install-oracle.sh --ora-swlib-bucket gs://oracle-software \
--instance-ssh-user ansible9 --instance-ssh-key ~/.ssh/id_rsa_bms_toolkit_ansible9 \
--ora-version 19 --cluster-type RAC --ora-swlib-path /u01/oracle_install --ora-swlib-type gcs \
--ora-asm-disks mntrl_asm.json \
--ora-data-mounts mntrl_data_mounts_config_mapper_dbsw.json \
--cluster-config mntrl_cluster.json --ora-data-diskgroup DATA --ora-reco-diskgroup RECO\
--ora-db-name orcl --ora-db-container false --backup-dest /u01/backups > /home/jcnarasimhan/050521-mntrl-instlln/bms-toolkit/logs/mntrl_rac_hadr_1 2>&1   &
[1] 1740
```
### 1a) Configuring 19c RAC Application Continuity
```commandline
[oracle@at-3793329-svr005 ~]$ srvctl status service -d orcl
[oracle@at-3793329-svr005 ~]$ srvctl add service -d orcl -s soepdb -preferred orcl1,orcl2
[oracle@at-3793329-svr005 ~]$ srvctl status service -d orcl
Service soepdb is not running.
[oracle@at-3793329-svr005 ~]$ srvctl config service -d orcl
Service name: soepdb
Server pool:
Cardinality: 2
Service role: PRIMARY
Management policy: AUTOMATIC
DTP transaction: false
AQ HA notifications: false
Global: false
Commit Outcome: false
Failover type:
Failover method:
Failover retries:
Failover delay:
Failover restore: NONE
Connection Load Balancing Goal: LONG
Runtime Load Balancing Goal: NONE
TAF policy specification: NONE
Edition:
Pluggable database name:
Hub service:
Maximum lag time: ANY
SQL Translation Profile:
Retention: 86400 seconds
Replay Initiation Time: 300 seconds
Drain timeout:
Stop option:
Session State Consistency: DYNAMIC
GSM Flags: 0
Service is enabled
Preferred instances: orcl1,orcl2
Available instances:
CSS critical: no
[oracle@at-3793329-svr005 ~]$ srvctl modify service -db orcl -service soepdb -failoverdelay 5
[oracle@at-3793329-svr005 ~]$ srvctl modify service -db orcl -service soepdb -failoverretry  60
[oracle@at-3793329-svr005 ~]$ srvctl modify service -db orcl -service soepdb -clbgoal SHORT
[oracle@at-3793329-svr005 ~]$ srvctl modify service -db orcl -service soepdb -rlbgoal SERVICE_TIME
[oracle@at-3793329-svr005 ~]$ srvctl config service -d orcl
Service name: soepdb
Server pool:
Cardinality: 2
Service role: PRIMARY
Management policy: AUTOMATIC
DTP transaction: false
AQ HA notifications: false
Global: false
Commit Outcome: false
Failover type:
Failover method:
Failover retries: 60
Failover delay: 5
Failover restore: NONE
Connection Load Balancing Goal: SHORT
Runtime Load Balancing Goal: SERVICE_TIME
TAF policy specification: NONE
Edition:
Pluggable database name:
Hub service:
Maximum lag time: ANY
SQL Translation Profile:
Retention: 86400 seconds
Replay Initiation Time: 300 seconds
Drain timeout:
Stop option:
Session State Consistency: DYNAMIC
GSM Flags: 0
Service is enabled
Preferred instances: orcl1,orcl2
Available instances:
CSS critical: no
[oracle@at-3793329-svr005 ~]$ srvctl status service -d orcl
Service soepdb is not running.
[oracle@at-3793329-svr005 ~]$ srvctl add service -db orcl -service soepdb_ac -commit_outcome TRUE -retention 86400 -preferred orcl1,orcl2
[oracle@at-3793329-svr005 ~]$ srvctl config service -d orcl -s soepdb_ac
Service name: soepdb_ac
Server pool:
Cardinality: 2
Service role: PRIMARY
Management policy: AUTOMATIC
DTP transaction: false
AQ HA notifications: false
Global: false
Commit Outcome: true
Failover type:
Failover method:
Failover retries:
Failover delay:
Failover restore: NONE
Connection Load Balancing Goal: LONG
Runtime Load Balancing Goal: NONE
TAF policy specification: NONE
Edition:
Pluggable database name:
Hub service:
Maximum lag time: ANY
SQL Translation Profile:
Retention: 86400 seconds
Replay Initiation Time: 300 seconds
Drain timeout:
Stop option:
Session State Consistency: DYNAMIC
GSM Flags: 0
Service is enabled
Preferred instances: orcl1,orcl2
Available instances:
CSS critical: no
[oracle@at-3793329-svr005 ~]$ srvctl modify service -db orcl -service soepdb_ac -failovertype TRANSACTION
[oracle@at-3793329-svr005 ~]$ srvctl modify service -db orcl -service soepdb_ac -failoverdelay 5
[oracle@at-3793329-svr005 ~]$ srvctl modify service -db orcl -service soepdb_ac -failoverretry  60
[oracle@at-3793329-svr005 ~]$ srvctl modify service -db orcl -service soepdb_ac -session_state STATIC
[oracle@at-3793329-svr005 ~]$ srvctl modify service -db orcl -service soepdb_ac -clbgoal SHORT
[oracle@at-3793329-svr005 ~]$ srvctl modify service -db orcl -service soepdb_ac -rlbgoal SERVICE_TIME
[oracle@at-3793329-svr005 ~]$ srvctl config service -d orcl -s soepdb_ac
Service name: soepdb_ac
Server pool:
Cardinality: 2
Service role: PRIMARY
Management policy: AUTOMATIC
DTP transaction: false
AQ HA notifications: true
Global: false
Commit Outcome: true
Failover type: TRANSACTION
Failover method:
Failover retries: 60
Failover delay: 5
Failover restore: NONE
Connection Load Balancing Goal: SHORT
Runtime Load Balancing Goal: SERVICE_TIME
TAF policy specification: NONE
Edition:
Pluggable database name:
Hub service:
Maximum lag time: ANY
SQL Translation Profile:
Retention: 86400 seconds
Replay Initiation Time: 300 seconds
Drain timeout:
Stop option:
Session State Consistency: STATIC
GSM Flags: 0
Service is enabled
Preferred instances: orcl1,orcl2
Available instances:
CSS critical: no
```
## 2) Perform pre-req: Download/Configure Swingbench

Edit the config file to point Swingbench to your RAC cluster's service configured with application continuity.

1) Download Swingbench from github repository onto the cloud VM and unzip: https://github.com/domgiles/swingbench-public/releases/download/production/swingbenchlatest.zip

2) Generate the "Order Entry" benchmark schema using Swingbench's oewizard tool, which will give the initial data against which Swingbench workloads can be run during simulation of each HA failure scenario:
```commandline
user@hadr-crdhost:~/swingbench/swingbench$ bin/oewizard -cl -create -cs //mntrlscan.company.brisbane.com/soepdb -scale 4 -u soe -p soe -ts soe -v -dba system -dbap orcl -tc 24
SwingBench Wizard
Author  :	 Dominic Giles
Version :	 2.6.0.1163
Running in Lights Out Mode using config file : ../wizardconfigs/oewizard.xml
Starting run
Starting script ../sql/soedgdrop2.sql
...
Data Generation Runtime Metrics
+-------------------------+-------------+
| Description             | Value       |
+-------------------------+-------------+
| Connection Time         | 0:00:00.003 |
| Data Generation Time    | 0:17:30.033 |
| DDL Creation Time       | 0:00:35.440 |
| Total Run Time          | 0:18:05.480 |
| Rows Inserted per sec   | 4,422       |
| Actual Rows Generated   | 4,654,350   |
| Commits Completed       | 468         |
| Batch Updates Completed | 23,544      |
+-------------------------+-------------+
...
```

3) Create a Swingbench config file.
   * As an example, the content in the following gpaste may be used (after changing the connect string to point to the RAC DB's SCAN name and service name that is configured with application continuity):
https://gist.github.com/jcnars/ef740adc194d3f437209805f5394145a

4) Test your Swingbench as follows to generate a workload for a short duration:
```commandline
user@hadr-crdhost:~/swingbench/swingbench/bin$ ./swingbench -c ../configs/mntrlscan_soepdb_ac.xml -r results.may.24.xml
Application :	 Swingbench
Author      :	 Dominic Giles
Version     :	 2.6.0.1163
...
```
## 3) Perform pre-req: Install necessary Python packages in your control-node
```commandline
user@hadr-crdhost:~/PycharmProjects/hadr$ pip3 install paramiko
user@hadr-crdhost:~/PycharmProjects/hadr$ pip install google-api-python-client
...
Installing collected packages: pyasn1, rsa, pyparsing, pyasn1-modules, protobuf, cachetools, httplib2, googleapis-common-protos, google-auth, uritemplate, google-auth-httplib2, google-api-core, google-api-python-client
  WARNING: The scripts pyrsa-decrypt, pyrsa-encrypt, pyrsa-keygen, pyrsa-priv2pub, pyrsa-sign and pyrsa-verify are installed in '/home/jcnarasimhan/.local/bin' which is not on PATH.
  Consider adding this directory to PATH or, if you prefer to suppress this warning, use --no-warn-script-location.
Successfully installed cachetools-5.2.0 google-api-core-2.8.2 google-api-python-client-2.51.0 google-auth-2.8.0 google-auth-httplib2-0.1.0 googleapis-common-protos-1.56.3 httplib2-0.20.4 protobuf-4.21.1 pyasn1-0.4.8 pyasn1-modules-0.2.8 pyparsing-3.0.9 rsa-4.8 uritemplate-4.1.1
user@hadr-crdhost:~/PycharmProjects/hadr$ pip3 install google-cloud-bare_metal_solution
...
Installing collected packages: google-cloud-bare-metal-solution
Successfully installed google-cloud-bare-metal-solution-1.0.1
user@hadr-crdhost:~/PycharmProjects/hadr$ python3
Python 3.9.2 (default, Feb 28 2021, 17:03:44)
[GCC 10.2.1 20210110] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> from google.cloud import bare_metal_solution_v2
>>> dir(bare_metal_solution_v2)
['BareMetalSolutionAsyncClient', 'BareMetalSolutionClient', 'CreateSnapshotSchedulePolicyRequest', 'CreateVolumeSnapshotRequest', 'DeleteSnapshotSchedulePolicyRequest', 'DeleteVolumeSnapshotRequest', 'GetInstanceRequest', 'GetLunRequest', 'GetNetworkRequest', 'GetSnapshotSchedulePolicyRequest', 'GetVolumeRequest', 'GetVolumeSnapshotRequest', 'Instance', 'ListInstancesRequest', 'ListInstancesResponse', 'ListLunsRequest', 'ListLunsResponse', 'ListNetworksRequest', 'ListNetworksResponse', 'ListSnapshotSchedulePoliciesRequest', 'ListSnapshotSchedulePoliciesResponse', 'ListVolumeSnapshotsRequest', 'ListVolumeSnapshotsResponse', 'ListVolumesRequest', 'ListVolumesResponse', 'Lun', 'Network', 'OperationMetadata', 'ResetInstanceRequest', 'ResetInstanceResponse', 'RestoreVolumeSnapshotRequest', 'SnapshotSchedulePolicy', 'UpdateSnapshotSchedulePolicyRequest', 'UpdateVolumeRequest', 'VRF', 'Volume', 'VolumeSnapshot', '__all__', '__builtins__', '__cached__', '__doc__', '__file__', '__loader__', '__name__', '__package__', '__path__', '__spec__', 'services', 'types']
>>> exit()
```
## 4) Clone this repo to your local directory in control-node
```commandline
user@jon2:~/python_development$ git clone "sso://team/bmx-sysops/bmx-infra-testing"
Cloning into 'bmx-infra-testing'...
...
```
## 5) Details: Kick off HA testing scenarios from command line:

1) Populate a json file that will be consumed by the code in the next step:
```json
(venv) user@hadr-crdhost:~/PycharmProjects/hadr$ cat user_inputs.json
{
  "ssh_key_file": "/home/jcnarasimhan/.ssh/id_rsa_bms_toolkit.ansible9",
  "ssh_user_name": "ansible9",
  "wwid_root_lun": "/dev/mapper/3600a09803831444a612b513161354445",
  "wwid_asm_lun": "/dev/mapper/3600a09803831444a685d513161313445",
  "swingbench_binary_location": "/home/jcnarasimhan/swingbench/swingbench/bin/charbench",
  "swingbench_config_file": "/home/jcnarasimhan/swingbench/swingbench/configs/mntrlscan_soepdb_ac_highertimeouts.xml",
  "nodes": [
    {  "node_name": "at-3793329-svr005",
       "host_ip": "172.16.110.1",
       "dict_oracle_logs":
        { "node1_asm_log" : "/u01/app/oracle/diag/asm/+asm/+ASM1/trace/alert_+ASM1.log",
          "node1_crs_log" : "/u01/app/oracle/diag/crs/at-3793329-svr005/crs/trace/alert.log",
          "node1_db_log"  : "/u01/app/oracle/diag/rdbms/orcl/orcl1/trace/alert_orcl1.log"
        }
    },
    {  "node_name": "at-3793329-svr006",
       "host_ip": "172.16.110.2",
       "dict_oracle_logs":
        { "node2_asm_log" : "/u01/app/oracle/diag/asm/+asm/+ASM2/trace/alert_+ASM2.log",
          "node2_crs_log" : "/u01/app/oracle/diag/crs/at-3793329-svr006/crs/trace/alert.log",
          "node2_db_log"  : "/u01/app/oracle/diag/rdbms/orcl/orcl2/trace/alert_orcl2.log"
        }
    }
  ]
}
```

2) The description of each optional/mandatory flag for the Python utility is as follows:
```commandline
(venv) user@hadr-crdhost:~/PycharmProjects/hadr$ python main_json.py -h
usage: main_json.py [-h] [-l] -s  -j  -n
Inject failure scenarios against a RAC cluster running DB workload generated via Swingbench
optional arguments:
  -h, --help            show this help message and exit
  -l , --log_dest       OS directory where logs will be created for this scenario run, default is `pwd`
required named arguments:
  -s , --scenario       Scenario to choose from choices of: testing, kernel_panic, shutdown, reset_api, hba_asm_lun, hba_root_lun,
                        hba_all_ports_down, oracleinst_down, listener_crash
  -j , --json_const     JSON file containing site-specific constants
  -n , --node_ip_to_test
                        DB node where fault injection needs to be done, should be a valid node contained in the site-specific json constants file
```

3) Take a note for valid strings to be passed as the `--scenario` from the above `help` output.

4) Invoke the code to simulate the desired scenario injecting fault in the desired node.
```commandline
(venv) user@hadr-crdhost:~/PycharmProjects/hadr$ ### We invoke the Python code to test failover scenarios as follows
(venv) user@hadr-crdhost:~/PycharmProjects/hadr$ python main_json.py -s oracleinst_down -j user_inputs.json -n 172.16.110.2 -l /home/jcnarasimhan/PycharmProjects/hadr/logs
```

5) View the log files created to observe the drop in Transaction Per Second (TPS) to 0 and how long it took for the BMX hosts to resume the Swingbench workload (this will be the observed `failover latency` or outage for that particular scenario).
