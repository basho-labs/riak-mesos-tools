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

import constants
import json
import requests
import time

from dcos import marathon
from kazoo.client import KazooClient


class CliCommand(object):
    def __init__(self, **kwargs):
        self.cmd=''
        self.help=''
        self.alias=''
        self.args=
        for key, val in kwargs.items():
            setattr(self, key, val)


class CliError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


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
            print constants.usage
            raise CliError('Not enough arguments for: ' + name)
    return [args, val]


def wait_for_url(url, debug_flag, seconds):
        if seconds == 0:
            return False
        try:
            r = requests.get(url)
            debug_request(debug_flag, r)
            if r.status_code == 200:
                return True
        except:
            pass
        time.sleep(1)
        return wait_for_url(url, debug_flag, seconds - 1)


def marathon_client(marathon_url=None):
    if marathon_url is not None:
        return marathon.Client(marathon_url)
    else:
        return marathon.create_client()


def zookeeper_command(hosts, command, path):
        zk = KazooClient(hosts=hosts)
        zk.start()
        node = path
        if command == 'get':
            data, stat = zk.get(node)
            return data.decode("utf-8")
        elif command == 'delete':
            zk.delete('/riak', recursive=True)
            return 'Successfully deleted ' + path
        else:
            return False
        zk.stop()


def debug(debug_flag, debug_string):
    if debug_flag:
        print('[DEBUG]' + debug_string + '[/DEBUG]')


def debug_request(debug_flag, r):
    debug(debug_flag, 'HTTP URL: ' + r.url)
    debug(debug_flag, 'HTTP Method: ' + r.request.method)
    debug(debug_flag, 'HTTP Body: ' + str(r.request.body))
    debug(debug_flag, 'HTTP Status: ' + str(r.status_code))
    debug(debug_flag, 'HTTP Response Text: ' + r.text)


def pparr(description, json_str, failure):
    try:
        obj_arr = json.loads(json_str)
        print(description + '[' + ', '.join(obj_arr.keys()) + ']')
    except:
        print(description + failure)


def ppobj(description, json_str, key, failure):
    try:
        obj = json.loads(json_str)
        print(description)
        if key == '':
            print(json.dumps(obj))
        else:
            print(json.dumps(obj[key]))
    except:
        print(description + failure)


def ppfact(description, json_str, key, failure):
    try:
        obj = json.loads(json_str)
        if key == '':
            print(description + json.dumps(obj))
        else:
            print(description + json.dumps(obj[key]))
    except:
        print(description + failure)


def help_dict():
        help = constants.help_dict
        # Aliases:
        help['framework config'] = help['framework']
        help['proxy config'] = help['proxy']
        help['cluster list'] = help['cluster']
        help['node list'] = help['node']
        return help


def help(cmd):
    return help_dict().get(cmd, False)
