#! /usr/bin/env python

#
#    Copyright (C) 2016 Basho Technologies, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Riak Mesos Framework CLI"""

import os
import sys
import traceback

from riak_mesos import commands, constants, util
from riak_mesos.config import RiakMesosConfig
from riak_mesos.util import CliError


def help_dict():
        help = constants.help_dict
        # Aliases:
        help['framework config'] = help['framework']
        help['cluster list'] = help['cluster']
        help['node list'] = help['node']
        help['director config'] = help['director']
        help['proxy'] = help['director']
        help['proxy config'] = help['director']
        help['proxy install'] = help['director install']
        help['proxy uninstall'] = help['director uninstall']
        help['proxy endpoints'] = help['director endpoints']
        help['proxy wait-for-service'] = help['director wait-for-service']
        return help


def help(cmd):
    return help_dict().get(cmd, False)


def validate_arg(opt, arg, arg_type='string'):
    if arg.startswith('-'):
        err = 'Invalid argument for opt: ' + opt + ' [' + arg + '].'
        raise CliError(err)
    if arg_type == 'integer' and not arg.isdigit():
        err = 'Invalid integer for opt: ' + opt + ' [' + arg + '].'
        raise CliError(err)


def test_flag(args, name):
    return name in args


def extract_flag(args, name):
    val = False
    if name in args:
        index = args.index(name)
        val = True
        del args[index]
    return [args, val]


def extract_option(args, name, default, arg_type='string'):
    val = default
    if name in args:
        index = args.index(name)
        if index+1 < len(args):
            val = args[index+1]
            validate_arg(name, val, arg_type)
            del args[index]
            del args[index]
        else:
            print(constants.usage)
            raise CliError('Not enough arguments for: ' + name)
    return [args, val]


class RiakMesosCli(object):
    def __init__(self, cli_args):
        args = {}

        def_conf_file = None
        sys_conf_file = '/etc/riak-mesos/config.json'
        usr_conf_file = '~/.config/riak-mesos/config.json'
        lcl_conf_file = '.config/riak-mesos/config.json'
        if os.path.isfile(lcl_conf_file):
            def_conf_file = lcl_conf_file
        elif os.path.isfile(usr_conf_file):
            def_conf_file = usr_conf_file
        elif os.path.isfile(sys_conf_file):
            def_conf_file = sys_conf_file

        cli_args, config_file = extract_option(cli_args, '--config',
                                               def_conf_file)
        cli_args, args['riak_file'] = extract_option(cli_args, '--file',
                                                     '')
        cli_args, args['lines'] = extract_option(cli_args, '--lines',
                                                 '1000')
        cli_args, args['force_flag'] = extract_flag(cli_args, '--force')
        cli_args, args['json_flag'] = extract_flag(cli_args, '--json')
        cli_args, args['verify_ssl_flag'] = extract_flag(cli_args,
                                                         '--verify-ssl')
        cli_args, args['help_flag'] = extract_flag(cli_args, '--help')
        cli_args, args['debug_flag'] = extract_flag(cli_args, '--debug')
        cli_args, args['cluster'] = extract_option(cli_args, '--cluster',
                                                   'default')
        cli_args, args['node'] = extract_option(cli_args, '--node', '')
        cli_args, args['bucket_type'] = extract_option(cli_args,
                                                       '--bucket-type',
                                                       'default')
        cli_args, args['props'] = extract_option(cli_args, '--props', '')
        cli_args, timeout = extract_option(cli_args, '--timeout',
                                           '60', 'integer')
        args['timeout'] = int(timeout)
        cli_args, num_nodes = extract_option(cli_args, '--nodes', '1',
                                             'integer')
        args['num_nodes'] = int(num_nodes)
        self.cmd = ' '.join(cli_args)
        util.debug(args['debug_flag'], 'Cluster: ' + args['cluster'])
        util.debug(args['debug_flag'], 'Node: ' + args['node'])
        util.debug(args['debug_flag'], 'Nodes: ' +
                   str(args['num_nodes']))
        util.debug(args['debug_flag'], 'Command: ' + self.cmd)

        if not os.path.isfile(config_file):
                raise CliError('No config file found')

        self.cfg = RiakMesosConfig(config_file, args)

    def run(self):
        cmd_desc = help(self.cmd)

        if self.cfg.args['help_flag'] and not cmd_desc:
            print(constants.usage)
            return 0
        elif self.cfg.args['help_flag']:
            print(cmd_desc)
            return 0

        if self.cmd == '':
            print('No commands executed')
            return
        elif self.cmd.startswith('-'):
            raise CliError('Unrecognized option: ' + self.cmd)
        elif not cmd_desc:
            raise CliError('Unrecognized command: ' + self.cmd)

        try:
            command_func_str = self.cmd.replace(' ', '_')
            command_func_str = command_func_str.replace('-', '_')
            util.debug(self.cfg.args['debug_flag'], 'Args: ' +
                       str(self.cfg.args))
            util.debug(self.cfg.args['debug_flag'], 'Command Func: ' +
                       command_func_str + '(cfg)')
            command_func = getattr(commands, command_func_str)
            command_func(self.cfg)
        except AttributeError as e:
                print('CliError: Unrecognized command: ' + self.cmd)
                if self.cfg.args['debug_flag']:
                        traceback.print_exc()
                        raise e

        return 0


def main():
    args = sys.argv[1:]
    if len(sys.argv) >= 2 and sys.argv[1] == 'riak':
        args = sys.argv[2:]
    if len(args) == 0:
        print(constants.usage)
        return 0
    if '--info' in args:
        print('Start and manage Riak nodes')
        return 0
    if '--version' in args:
        print('Riak Mesos Framework Version ' + constants.version)
        return 0
    if '--config-schema' in args:
        print('{}')
        return 0
    debug = False
    if '--debug' in args:
        debug = True

    try:
        cli = RiakMesosCli(args)
        return cli.run()
    except CliError as e:
        print('CliError: ' + str(e))
        if debug:
            traceback.print_exc()
            raise e
        return 1
    except Exception as e:
        print(e)
        if debug:
            traceback.print_exc()
            raise e
        return 1

if __name__ == '__main__':
    main()
