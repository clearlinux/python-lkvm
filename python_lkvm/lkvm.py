#
# Copyright (c) 2015 Intel Corporation
#
# Author: Morales, Victor <victor.morales@intel.com>
# Author: Munoz, Obed N <obed.n.munoz@intel.com>
# Author: Simental Magana, Marcos <marcos.simental.magana@intel.com>
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
#

import logging
import os
import psutil
import six
import subprocess
import sys

LKVM_PATH='/usr/bin/lkvm'

logging.basicConfig(format='%(message)s', level=logging.INFO)
LOG = logging.getLogger(__name__)

class LKVMException(Exception):
    pass


class LKVMInstance(object):
    pass


class Client(object):

    def __init__(self):
        self._root_helper = None

    @property
    def root_helper(self):
        return self._root_helper

    @root_helper.setter
    def root_helper(self, value):
        self._root_helper = value

    def _get_instance_info(self, pid):
        if isinstance(pid, six.string_types):
            pid = int(pid)
        try:
            args = psutil.Process(pid).cmdline()[2:]
        except NoSuchProcess:
            raise LKVMException("PID %s not found" % pid)
        props = {args[i][2:]: args[i+1] for i in range(0, len(args), 2)}
        LOG.debug('Properties found : ' + str(props))

        return type('LKVMInstance', (object,), props)

    def _execute(self, cmd, *args, **kwargs):
        """Helper method to shell out and execute a command through subprocess.

        :param cmd:            Command
        :type cmd:             string
        :param args:           Arguments
        :type args:            string

        """

        if hasattr(os, 'geteuid') and os.geteuid() != 0 and not self._root_helper:
            return

        command = [LKVM_PATH]
        if self._root_helper:
            command = [self._root_helper] + command
        command.append(cmd)
        command.extend(*args)

        command = [str(c) for c in command]

        LOG.debug('Executing command : %s ', command)
        if kwargs.get('background'):
            command.insert(0, 'nohup')
            command = ' '.join(command) + ' >/dev/null 2>&1'
            subprocess.Popen(command, shell=True)
        else:
            _PIPE = subprocess.PIPE
            obj = subprocess.Popen(command,
                                   stdin=_PIPE,
                                   stdout=_PIPE,
                                   stderr=_PIPE)
            try:
                result = obj.communicate()
                obj.stdin.close()
            except OSError as err:
                if isinstance(err, ProcessExecutionError):
                    err_msg = ('{e[description]}\ncommand: {e[cmd]}\n'
                               'exit code: {e[exit_code]}\nstdout: {e[stdout]}\n'
                               'stderr: {e[stderr]}').format(e=err)
                    raise LKVMException(err_msg)
            if result[1]:
                raise LKVMException(result[1])

            return result[0]

    def run(self, cpus, mem, shmem, console, kernel, params,
            network, name=None, disk=None, balloon=False,
            vnc=False, gtk=False, sdl=False, rng=False,
            plan9=False, dev=None, tty=None, sandbox=None,
            hugetlbs=None, initrd=None, firmware=None,
            no_dhcp=False):
        """Start the virtual machine

        :param name:           Name of the guest
        :type name:            string
        :param cpus:           Number of CPUs
        :type cpus:            integer
        :param mem:            Virtual machine memory size in MiB.
        :type mem:             integer
        :param shmem:          Share host shmem with guest via pci device
        :type shmem:           string
        :param disk:           Disk image or rootfs directory
        :type disk:            string
        :param balloon:        Enable virtio balloon
        :type balloon:         boolean
        :param vnc:            Enable VNC framebuffer
        :type vnc:             boolean
        :param gtk:            Enable GTK framebuffer
        :type gtk:             boolean
        :param sdl:            Enable SDL framebuffer
        :type sdl:             boolean
        :param rng:            Enable virtio Random Number Generator
        :type rng:             boolean
        :param plan9:          Enable virtio 9p to share files between host and guest
        :type plan9:           boolean
        :param console:        Console to use
        :type console:         string
        :param dev:            KVM device file
        :type dev:             string
        :param tty:            Remap guest TTY into a pty on the host
        :type tty:             string
        :param sandbox:        Run this script when booting into custom rootfs
        :type sandbox:         string
        :param hugetlbfs:      Hugetlbfs path
        :type hugetlbfs:       string
        :param kernel:         Kernel to boot in virtual machine
        :type kernel:          string
        :param initrd:         Initial RAM disk image
        :type initrd:          integer
        :param params:         Kernel command line arguments
        :type params:          string
        :param firmware:       Firmware image to boot in virtual machine
        :type firmware:        string
        :param network:        Create a new guest NIC
        :type network:         string
        :param no_dhcp:        Disable kernel DHCP in rootfs mode
        :type no_dhcp:         boolean

        """

        _params = []

        # Basic options


        _params.extend(['--cpus', cpus,
                       '--mem', mem,
                       '--shmem', shmem])

        if name:
            _params.extend(['--name', name])
        if console in ['serial', 'virtio', 'hv']:
            _params.extend(['--console', console])
        if balloon:
            _params.append('--balloon')
        if vnc:
            _params.append('--vnc')
        if gtk:
            _params.append('--gtk')
        if sdl:
            _params.append('--sdl')
        if rng:
            _params.append('--rng')
        if plan9:
            _params.append('--9p')
        if disk:
            _params.extend(['--disk', disk])
        if dev:
            _params.extend(['--dev', dev])
        if tty:
            _params.extend(['--tty', tty])
        if sandbox:
            _params.extend(['--sandbox', sandbox])
        if hugetlbs:
            _params.extend(['--hugetlbs', hugetlbs])

        # Kernel options

        _params.extend(['--kernel', kernel,
                       '--params', '"%s"' % params])

        if initrd:
            _params.extend(['--initrd', initrd])
        if firmware:
            _params.extend(['--firmware', firmware])

        # Networking options

        _params.extend(['--network', network])

        if no_dhcp:
            _params.append('--no-dhcp')

        self._execute('run', _params, background=True)

    def setup(self, name):
        """
        Setup a new virtual machine

        :param name:           Instance name
        :type name:            string

        """
        params = ['--name', name]

        return self._execute('setup', params)

    def pause(self, all=False, name=None):
        """Pause the virtual machine

        :param all:            Pause all instances
        :type all:             boolean
        :param name:           Instance name
        :type name:            string

        """
        params = []
        if all:
            params.append('--all')
        elif name:
            params.extend(['--name', name])
        else:
            return

        self._execute('pause', params)

    def resume(self, all=False, name=None):
        """Resume the virtual machine

        :param all:            Resume all instances
        :type all:             boolean
        :param name:           Instance name
        :type name:            string

        """
        params = []
        if all:
            params.append('--all')
        elif name:
            params.extend(['--name', name])
        else:
            return

        self._execute('resume', params)

    def list_instances(self, run=True, rootfs=True):
        """Print a list of running instances on the host.

        :param run:            List running instances
        :type cmd:             boolean
        :param rootfs:         List rootfs instances
        :type args:            boolean

        """
        params = []
        if run:
            params.append('--run')
        if rootfs:
            params.append('--rootfs')

        output = self._execute('list', params)

        instances = []
        if output:
           results = output.split('\n')
           if len(results) > 2 :
              for result in results[2:-1]:
                  ins = result.split()
                  instance = self._get_instance_info(ins[0])
                  instance.pid = ins[0]
                  instance.name = ins[1]
                  instance.state = ins[2]
                  instances.append(instance)

        return instances

    def balloon(self, name, amount, balloon_options):
        """Inflate or deflate the virtio balloon

        :param name:            Instance name
        :type name:             string
        :param amount:          Amount to inflate/deflate (in MB)
        :type amount:           integer
        :param ballon_options:

        """
        params = ['name', name]
        if balloon_options == 'inflate':
            params.extend(['--inflate', amount])
        elif balloon_options == 'deflate':
            params.extend(['--deflate', amount])

        self._execute('balloon', params)

    def stop(self, all=False, name=None):
        """Stop a running instance

        :param all:            Stop all instances
        :type all:             boolean
        :param name:           Instance name
        :type name:            string

        """
        params = []
        if all:
            params.append('--all')
        elif name:
            params.extend(['--name', name])
        else:
            return

        self._execute('stop', params)

    def stat(self, memory=True, all=False, name=None):
        """Print statistics about a running instance

        :param memory:         Display memory statistics
        :type memory:          boolean
        :param all:            All instances
        :type all:             boolean
        :param name:           Instance name
        :type name:            string

        """
        return  # This method is not supported by lkvm client

        params = ['--memory']
        if all:
            params.append('--all')
        elif name:
            params.extend(['--name', name])
        else:
            return

        output = self._execute('stat', params)

        instances = []
        if len(output) > 1:
           if len(results) > 2 :
              for result in results[2:-1]:
                  ins = result.split()
                  instance = KVMInstance(ins[0], ins[1], ins[2])
                  instances.append(instance)

        return instances

    def sandbox(self, cpus, mem, shmem, console, kernel, params,
            network, name=None, disk=None, balloon=False,
            vnc=False, gtk=False, sdl=False, rng=False,
            plan9=False, dev=None, tty=None, sandbox=None,
            hugetlbs=None, initrd=None, firmware=None,
            no_dhcp=False):
        """Run a command in a sandboxed guest

        :param name:           Name of the guest
        :type name:            string
        :param cpus:           Number of CPUs
        :type cpus:            integer
        :param mem:            Virtual machine memory size in MiB.
        :type mem:             integer
        :param shmem:          Share host shmem with guest via pci device
        :type shmem:           string
        :param disk:           Disk image or rootfs directory
        :type disk:            string
        :param balloon:        Enable virtio balloon
        :type balloon:         boolean
        :param vnc:            Enable VNC framebuffer
        :type vnc:             boolean
        :param gtk:            Enable GTK framebuffer
        :type gtk:             boolean
        :param sdl:            Enable SDL framebuffer
        :type sdl:             boolean
        :param rng:            Enable virtio Random Number Generator
        :type rng:             boolean
        :param plan9:          Enable virtio 9p to share files between host and guest
        :type plan9:           boolean
        :param console:        Console to use
        :type console:         string
        :param dev:            KVM device file
        :type dev:             string
        :param tty:            Remap guest TTY into a pty on the host
        :type tty:             string
        :param sandbox:        Run this script when booting into custom rootfs
        :type sandbox:         string
        :param hugetlbfs:      Hugetlbfs path
        :type hugetlbfs:       string
        :param kernel:         Kernel to boot in virtual machine
        :type kernel:          string
        :param initrd:         Initial RAM disk image
        :type initrd:          integer
        :param params:         Kernel command line arguments
        :type params:          string
        :param firmware:       Firmware image to boot in virtual machine
        :type firmware:        string
        :param network:        Create a new guest NIC
        :type network:         string
        :param no_dhcp:        Disable kernel DHCP in rootfs mode
        :type no_dhcp:         boolean

        """

        _params = []

        # Basic options


        _params.extend(['--cpus', cpus,
                       '--mem', mem,
                       '--shmem', shmem])

        if name:
            _params.extend(['--name', name])
        if console in ['serial', 'virtio', 'hv']:
            _params.extend(['--console', console])
        if balloon:
            _params.append('--balloon')
        if vnc:
            _params.append('--vnc')
        if gtk:
            _params.append('--gtk')
        if sdl:
            _params.append('--sdl')
        if rng:
            _params.append('--rng')
        if plan9:
            _params.append('--9p')
        if disk:
            _params.extend(['--disk', disk])
        if dev:
            _params.extend(['--dev', dev])
        if tty:
            _params.extend(['--tty', tty])
        if sandbox:
            _params.extend(['--sandbox', sandbox])
        if hugetlbs:
            _params.extend(['--hugetlbs', hugetlbs])

        # Kernel options

        _params.extend(['--kernel', kernel,
                       '--params', '"%s"' % params])

        if initrd:
            _params.extend(['--initrd', initrd])
        if firmware:
            _params.extend(['--firmware', firmware])

        # Networking options

        _params.extend(['--network', network])

        if no_dhcp:
            _params.append('--no-dhcp')

        self._execute('sandbox', _params, background=True)

    def is_supported(self):
        return os.path.isfile(LKVM_PATH)
