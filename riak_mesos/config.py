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
        self.config_file = config_file
        if self.config_file is not None:
            with open(self.config_file) as data_file:
                self._config = json.load(data_file)
        else:
            self._config = {}

    def _get_config_value(self, *keys):
        value = self._config
        for key in keys:
            value = value[key]
        return value

    def _get_resource_url(self, key):
        return self._get_config_value('resources', key)

    def _get_resource_urls(self):
        return self._get_config_value('resources').values()

    def _get_riak_resources(self):
        resources = self._get_config_value('resources')
        riak_resources = {}
        for resource in resources:
            if resource.startswith('riak-'):
                riak_resources[resource] = resources[resource]
        return riak_resources

    def _from_conf(self, key, subkey, env_name, conf):
        if env_name not in conf:
            return
        if 'riak' not in self._config:
            self._config['riak'] = {}
        if subkey is not None:
            if key not in self._config['riak']:
                self._config['riak'][key] = {}
            self._config['riak'][key][subkey] = conf[env_name]
        else:
            self._config['riak'][key] = conf[env_name]

    def from_marathon(self, ctx):
        if self.config_file is not None:
            return
        client = ctx.marathon_client()
        app = {}
        try:
            app = client.get_app(ctx.framework)
        except Exception as e:
            ctx.cli_error("Unable to to find installed framework in marathon ("
                          + e.message + ")")
        conf = app['env']
        # TODO: Get urls from uris, not needed yet
        self._from_conf('framework-name', None, 'RIAK_MESOS_NAME', conf)
        self._from_conf('zk', None, 'RIAK_MESOS_ZK', conf)
        self._from_conf('master', None, 'RIAK_MESOS_MASTER', conf)
        self._from_conf('user', None, 'RIAK_MESOS_USER', conf)
        self._from_conf('role', None, 'RIAK_MESOS_ROLE', conf)
        self._from_conf('hostname', None, 'RIAK_MESOS_HOSTNAME', conf)
        self._from_conf('ip', None, 'RIAK_MESOS_IP', conf)
        self._from_conf('failover-timeout', None,
                        'RIAK_MESOS_FAILOVER_TIMEOUT', conf)
        self._from_conf('auth-provider', None, 'RIAK_MESOS_PROVIDER', conf)
        self._from_conf('auth-principal', None, 'RIAK_MESOS_PRINCIPAL', conf)
        self._from_conf('auth-secret-file', None,
                        'RIAK_MESOS_SECRET_FILE', conf)
        self._from_conf('director', 'url', 'RIAK_MESOS_DIRECTOR_URL', conf)
        if 'RIAK_MESOS_DIRECTOR_CPUS' in conf:
            self._config['riak']['director']['cpus'] = \
                float(conf['RIAK_MESOS_DIRECTOR_CPUS'])
        if 'RIAK_MESOS_DIRECTOR_MEM' in conf:
            self._config['riak']['director']['mem'] = \
                float(conf['RIAK_MESOS_DIRECTOR_MEM'])
        if 'RIAK_MESOS_DIRECTOR_PUBLIC' in conf:
            if conf['RIAK_MESOS_DIRECTOR_PUBLIC'] == 'true':
                self._config['riak']['director']['use-public'] = True
            else:
                self._config['riak']['director']['use-public'] = False
        self._from_conf('scheduler', 'package',
                        'RIAK_MESOS_SCHEDULER_PKG', conf)
        self._from_conf('scheduler', 'constraints',
                        'RIAK_MESOS_CONSTRAINTS', conf)
        self._from_conf('executor', 'package',
                        'RIAK_MESOS_EXECUTOR_PKG', conf)
        self._from_conf('executor', 'cpus',
                        'RIAK_MESOS_EXECUTOR_CPUS', conf)
        self._from_conf('executor', 'mem',
                        'RIAK_MESOS_EXECUTOR_MEM', conf)
        self._from_conf('node', 'network_interface_name',
                        'RIAK_MESOS_NODE_IFACE', conf)
        self._from_conf('node', 'cpus', 'RIAK_MESOS_NODE_CPUS', conf)
        self._from_conf('node', 'mem', 'RIAK_MESOS_NODE_MEM', conf)
        self._from_conf('node', 'disk', 'RIAK_MESOS_NODE_DISK', conf)
        self._from_conf('node', 'package', 'RIAK_MESOS_RIAK_PKG', conf)
        self._from_conf('node', 'patches-package',
                        'RIAK_MESOS_PATCHES_PKG', conf)
        self._from_conf('node', 'explorer-package',
                        'RIAK_MESOS_EXPLORER_PKG', conf)

    def framework_marathon_json(self, ctx=None):
        mj = {}
        mj['id'] = self.get('framework-name')
        mj['instances'] = self.get('instances')
        mj['user'] = self.get('user')
        mj['cpus'] = self.get('scheduler', 'cpus')
        mj['mem'] = self.get('scheduler', 'mem')
        mj['ports'] = [0]
        # TODO: Change these once scheduler is updated
        # mj['fetch'] = []
        # mj['fetch'].append(
        #     {'uri': self.get('scheduler', 'url')})
        # mj['fetch'].append(
        #     {'uri': self.get('executor', 'url'),
        #      'extract': False})
        # mj['fetch'].append(
        #     {'uri': self.get('node', 'url'),
        #      'extract': False})
        # mj['fetch'].append(
        #     {'uri': self.get('node', 'patches-url'),
        #      'extract': False})
        # mj['fetch'].append(
        #     {'uri': self.get('node', 'explorer-url'),
        #      'extract': False})
        # mj['cmd'] = './bin/ermf-scheduler'
        mj['uris'] = self._get_resource_urls()
        mj['cmd'] = './riak_mesos_scheduler/bin/ermf-scheduler'
        if self.get('constraints') != '':
            mj['constraints'] = self.get('constraints')
        mj['env'] = {}
        mj['env']['RIAK_MESOS_DIRECTOR_URL'] = self.get('director', 'url')
        mj['env']['RIAK_MESOS_DIRECTOR_CPUS'] = \
            str(self.get('director', 'cpus'))
        mj['env']['RIAK_MESOS_DIRECTOR_MEM'] = str(self.get('director', 'mem'))
        if self.get('director', 'use-public') != '':
            if self.get('director', 'use-public'):
                mj['env']['RIAK_MESOS_DIRECTOR_PUBLIC'] = 'true'
            else:
                mj['env']['RIAK_MESOS_DIRECTOR_PUBLIC'] = 'false'
        mj['env']['RIAK_MESOS_NAME'] = self.get('framework-name')
        mj['env']['RIAK_MESOS_ZK'] = self.get('zk')
        mj['env']['RIAK_MESOS_MASTER'] = self.get('master')
        mj['env']['RIAK_MESOS_USER'] = self.get('user')
        mj['env']['RIAK_MESOS_SCHEDULER_PKG'] = self._get_resource_url(
            'scheduler').rsplit('/', 1)[-1]
        mj['env']['RIAK_MESOS_EXECUTOR_PKG'] = self._get_resource_url(
            'executor').rsplit('/', 1)[-1]
        mj['env']['RIAK_MESOS_RIAK_PKG'] = self._get_resource_url(
            'node').rsplit('/', 1)[-1]
        mj['env']['RIAK_MESOS_PATCHES_PKG'] = self._get_resource_url(
            'node-patches').rsplit('/', 1)[-1]
        mj['env']['RIAK_MESOS_EXPLORER_PKG'] = self._get_resource_url(
            'node-explorer').rsplit('/', 1)[-1]
        mj['env']['RIAK_MESOS_RIAK_URLS'] = json.dumps(
            self._get_riak_resources())
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
        if self.get('node', 'network_interface_name') != '':
            mj['env']['RIAK_MESOS_NODE_IFACE'] = \
                    str(self.get('node', 'network_interface_name'))
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
        if ctx is not None and ctx.attach:
            mj['env']['RIAK_MESOS_ATTACH'] = 'True'
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
        framework = self.get('framework-name')
        director_marathon_name = "-".join((framework, cluster, 'director'))
        director_marathon_conf = {
            'id': '/' + director_marathon_name,
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
            # 'fetch': [{'uri': self.get('director', 'url')}],
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
        if self.get('director', 'use-public') is True:
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
        elif key in self._config and subkey1 in self._config[key]:
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
