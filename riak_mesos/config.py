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


class RiakMesosConfig(object):
    def __init__(self, config_file):
        if config_file is not None:
            with open(config_file) as data_file:
                self._config = json.load(data_file)
        else:
            self._config = {}

    def framework_marathon_json(self):
        mj = {}
        mj['id'] = self.get('framework-name')
        mj['instances'] = self.get('instances')
        mj['user'] = self.get('user')
        mj['cpus'] = self.get('scheduler', 'cpus')
        mj['mem'] = self.get('scheduler', 'mem')
        mj['ports'] = [0]
        mj['fetch'] = []
        mj['fetch'].append({ 'uri': self.get('scheduler', 'url')})
        mj['fetch'].append({ 'uri': self.get('executor', 'url'), 'extract': false })
        mj['fetch'].append({ 'uri': self.get('node', 'url'), 'extract': false })
        mj['fetch'].append({ 'uri': self.get('node', 'patches-url'), 'extract': false })
        mj['fetch'].append({ 'uri': self.get('node', 'explorer-url'), 'extract': false })
        mj['cmd'] = './bin/ermf-scheduler'
        if self.get('constraints') != '':
            mj['constraints'] = self.get('constraints')
        mj['env'] = {}
        mj['env']['RIAK_MESOS_NAME'] = self.get('framework-name')
        mj['env']['RIAK_MESOS_ZK'] = self.get('zk')
        mj['env']['RIAK_MESOS_MASTER'] = self.get('master')
        mj['env']['RIAK_MESOS_USER'] = self.get('user')
        mj['env']['RIAK_MESOS_SCHEDULER_PKG'] = self.get(
            'scheduler', 'url').rsplit('/', 1)[-1]
        mj['env']['RIAK_MESOS_EXECUTOR_PKG'] = self.get(
            'executor', 'url').rsplit('/', 1)[-1]
        mj['env']['RIAK_MESOS_RIAK_PKG'] = self.get(
            'node', 'url').rsplit('/', 1)[-1]
        mj['env']['RIAK_MESOS_PATCHES_PKG'] = self.get(
            'node', 'patches-url').rsplit('/', 1)[-1]
        mj['env']['RIAK_MESOS_EXPLORER_PKG'] = self.get(
            'node', 'explorer-url').rsplit('/', 1)[-1]
        if self.get('scheduler', 'constraints') != '':
            mj['env']['RIAK_MESOS_CONSTRAINTS'] = json.dumps(
                self.get('scheduler', 'constraints'))
        if self.get('auth-principal') != '':
            mj['env']['RIAK_MESOS_PRINCIPAL'] = self.get('auth-principal')
        if self.get('auth-provider') != '':
            mj['env']['RIAK_MESOS_PROVIDER'] = self.get('auth-provider')
        if self.get('auth-secret-file') != '':
            mj['env']['RIAK_MESOS_SECRET_FILE'] = self.get('auth-secret-file')
        if self.get('role') != '':
            mj['env']['RIAK_MESOS_ROLE'] = self.get('role')
        if self.get('ip') != '':
            mj['env']['RIAK_MESOS_IP'] = self.get('ip')
        if self.get('hostname') != '':
            mj['env']['RIAK_MESOS_HOSTNAME'] = self.get('hostname')
        if self.get('failover-timeout') != '':
            mj['env']['RIAK_MESOS_FAILOVER_TIMEOUT'] = str(self.get(
                'failover-timeout'))
        if self.get('node', 'cpus') != '':
            mj['env']['RIAK_MESOS_NODE_CPUS'] = str(self.get('node', 'cpus'))
        if self.get('node', 'mem') != '':
            mj['env']['RIAK_MESOS_NODE_MEM'] = str(self.get('node', 'mem'))
        if self.get('node', 'disk') != '':
            mj['env']['RIAK_MESOS_NODE_DISK'] = str(self.get('node', 'disk'))
        if self.get('executor', 'cpus') != '':
            mj['env']['RIAK_MESOS_EXECUTOR_CPUS'] = str(self.get(
                'executor', 'cpus'))
        if self.get('executor', 'mem') != '':
            mj['env']['RIAK_MESOS_EXECUTOR_MEM'] = str(self.get(
                'executor', 'mem'))
        healthcheck = {'path': '/healthcheck'}
        healthcheck.update({'portIndex': 0}),
        healthcheck.update({'protocol': 'HTTP'})
        healthcheck.update({'gracePeriodSeconds': self.get(
            'healthcheck-grace-period-seconds')})
        healthcheck.update({'intervalSeconds': self.get(
            'healthcheck-interval-seconds')})
        healthcheck.update({'timeoutSeconds': self.get(
            'healthcheck-timeout-seconds')})
        healthcheck.update({'maxConsecutiveFailures': self.get(
            'healthcheck-max-consecutive-failures')})
        healthcheck.update({'ignoreHttp1xx': False})
        mj['healthChecks'] = []
        mj['healthChecks'].append(healthcheck)
        return mj

    def framework_marathon_string(self):
        return json.dumps(self.framework_marathon_json())

    def director_marathon_json(self, cluster):
        director_marathon_conf = {
            'id': '/' + cluster + '-director',
            'cmd': './riak_mesos_director/bin/ermf-director',
            'cpus': self.get('director', 'cpus'),
            'mem': self.get('director', 'mem'),
            'ports': [0, 0, 0],
            'instances': 1,
            'env': {
                'USE_SUPER_CHROOT': "false",
                'DIRECTOR_ZK': self.get('zk'),
                'DIRECTOR_FRAMEWORK': self.get('framework-name'),
                'DIRECTOR_CLUSTER': cluster
            },
            'uris': [self.get('director', 'url')],
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
        if self.get('director', 'use-public'):
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
            if (key in self._config and subkey1 in self._config[key] and
                    subkey2 in self._config[key][subkey1]):
                return self._config[key][subkey1][subkey2]
        if key in self._config and subkey1 in self._config[key]:
            return self._config[key][subkey1]
        return ''

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
