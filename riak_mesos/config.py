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

import json
import requests
import util


class RiakMesosConfig(object):
    def __init__(self, override_file=None):
        with open(override_file) as data_file:
            self._config = json.load(data_file)

    def _fw_arg(self, name, var_name):
        if self.get(var_name) != '':
            return ' -' + name + '=' + self.get(var_name)
        return ''

    def _fw_arg_val(self, name, val):
        if val != '':
            return ' -' + name + '=' + str(val)
        return ''

    def framework_marathon_json(self):
        cmd = 'riak_mesos_framework/framework_linux_amd64'
        cmd += self._fw_arg('master', 'master')
        cmd += self._fw_arg('zk', 'zk')
        cmd += self._fw_arg('name', 'framework-name')
        cmd += self._fw_arg('user', 'user')
        cmd += self._fw_arg('ip', 'ip')
        cmd += self._fw_arg('hostname', 'hostname')
        cmd += self._fw_arg('log', 'log')
        cmd += self._fw_arg('role', 'role')
        cmd += self._fw_arg('mesos_authentication_provider', 'auth-provider')
        cmd += self._fw_arg('mesos_authentication_principal', 'auth-principal')
        cmd += self._fw_arg('mesos_authentication_secret_file',
                            'auth-secret-file')
        cmd += self._fw_arg_val('node_cpus', self.get('node', 'cpus'))
        cmd += self._fw_arg_val('node_mem', self.get('node', 'mem'))
        cmd += self._fw_arg_val('node_disk', self.get('node', 'disk'))
        cmd += ' ' + self.get('flags') if self.get('flags') != '' else ''
        healthcheck = {
            'path': '/healthcheck',
            'portIndex': 0,
            'protocol': 'HTTP',
            'gracePeriodSeconds':
            self.get('healthcheck-grace-period-seconds'),
            'intervalSeconds':
            self.get('healthcheck-interval-seconds'),
            'timeoutSeconds':
            self.get('healthcheck-timeout-seconds'),
            'maxConsecutiveFailures':
            self.get('healthcheck-max-consecutive-failures'),
            'ignoreHttp1xx': False
        }
        return {
            'id': self.get('framework-name'),
            'instances': self.get('instances'),
            'cpus': self.get('cpus'),
            'mem': self.get('mem'),
            'ports': [0, 0],
            'uris': [self.get('url')],
            'env': {'USE_SUPER_CHROOT': self.get('super-chroot')},
            'cmd': cmd,
            'healthChecks': [healthcheck]
        }

    def framework_marathon_string(self):
        return json.dumps(self.framework_marathon_json())

    def director_marathon_json(self, cluster):
        director_marathon_conf = {
            'id': '/riak-director',
            'cmd': self.get_any('director', 'cmd'),
            'cpus': 0.5,
            'mem': 500.0,
            'ports': [0, 0, 0, 0],
            'instances': 1,
            'env': {
                'USE_SUPER_CHROOT': self.get('super-chroot'),
                'DIRECTOR_ZK': self.get('zk'),
                'DIRECTOR_FRAMEWORK': self.get('framework-name'),
                'DIRECTOR_CLUSTER': cluster
            },
            'uris': [self.get_any('director', 'url')],
            'healthChecks': [
                {
                    'protocol': 'HTTP',
                    'path': '/health',
                    'gracePeriodSeconds': 3,
                    'intervalSeconds': 10,
                    'portIndex': 2,
                    'timeoutSeconds': 10,
                    'maxConsecutiveFailures': 3
                }
            ]
        }
        if self.get_any('director', 'use-public'):
            director_marathon_conf['acceptedResourceRoles'] = ['public']
        return director_marathon_conf

    def director_marathon_string(self, cluster):
        return json.dumps(self.director_marathon_json(cluster))

    def string(self):
        return json.dumps(self._config)

    def json(self):
        return self._config

    def get(self, key, subkey=None):
        return self.get_any('riak', key, subkey)

    def get_any(self, key, subkey1, subkey2=None):
        if subkey2 is not None and subkey2 is not None:
            return self._config[key][subkey1][subkey2]
        return self._config[key][subkey1]

    def _merge(self, override):
        for k in override.keys():
            if isinstance(override[k], dict):
                for j in override[k].keys():
                    if isinstance(override[k][j], dict):
                        for i in override[k][j].keys():
                            self._config[k][j][i] = override[k][j][i]
                    else:
                        self._config[k][j] = override[k][j]
            else:
                self._config[k] = override[k]

    def zk_api_url(self):
        try:
            path = '/riak/frameworks/' + self.get('framework-name') + '/uri'
            url = util.zookeeper_command(self.get('zk'), 'get', path)
            if url:
                return url.strip() + '/'
            return False
        except:
            return False

    def marathon_api_url(self):
        try:
            client = util.marathon_client(self.get_any('marathon', 'url'))
            tasks = client.get_tasks(self.get('framework-name'))
            if len(tasks) != 0:
                host = tasks[0]['host']
                port = tasks[0]['ports'][0]
                return 'http://' + host + ':' + str(port) + '/'
            return False
        except:
            return False

    def dcos_api_url(self):
        try:
            from dcos import util
            framework = self.get('framework-name')
            client = util.marathon_client(self.get_any('marathon', 'url'))
            tasks = client.get_tasks(self.get('framework-name'))
            if len(tasks) == 0:
                raise util.CliError('Riak Mesos Framework is not running.')
            service_url = util.get_config().get('core.dcos_url').rstrip('/')
            service_url += '/service/' + framework + '/'
            r = requests.get(service_url + 'healthcheck')
            if r.status_code == 200:
                return service_url
            return False
        except:
            return False

    def api_url(self):
        try:
            service_url = self.dcos_api_url()
            if service_url:
                return service_url + 'api/v1/'
            service_url = self.marathon_api_url()
            if service_url:
                return service_url + 'api/v1/'
            service_url = self.zk_api_url()
            if service_url:
                return service_url + 'api/v1/'
            error = 'Unable to connect to DCOS Server, Marathon, or Zookeeper.'
            raise util.CliError(error)
        except Exception as e:
            raise util.CliError('Unable to find api url: ' + e.message)
