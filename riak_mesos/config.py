import os
import json
import requests
import sys

from riak_mesos import Client, CliError, usage
from sys import platform as _platform


# Util
def is_dcos():
    if len(sys.argv) >= 2:
        return sys.argv[1] == 'riak'
    return False


def create_client(marathon_url):
    if is_dcos():
        from dcos import marathon
        return marathon.create_client()
    else:
        return Client(marathon_url)


# Config
class Config(object):
    def __init__(self, override_file=None):
        self._config = self.default_framework_config()
        if override_file is not None:
            with open(override_file) as data_file:
                data = json.load(data_file)
                self._merge(data)

    def zktool_command(self, command, path):
        tool = ''
        command = ''
        if _platform == 'linux' or _platform == 'linux2':
            tool = os.path.dirname(__file__) + '/' + 'zktool_linux_amd64'
        elif _platform == 'darwin':
            tool = os.path.dirname(__file__) + '/' + 'zktool_darwin_amd64'
        else:
            return False
        if command == 'get':
            args = tool + ' -zk=' + self.get('zk') + ' -name=' + path
            args += ' -command=zk-get-data'
            data = os.popen(args).read()
            if data.strip() == 'zk: node does not exist':
                return False
            elif data.strip() == 'zk: could not connect to a server':
                return False
            return data
        elif command == 'delete':
            args = tool + ' -zk=' + self.get('zk') + ' -name=' + path
            args += ' -command=zk-delete'
            output = os.popen(args).read()
            output += os.popen(args).read()
            output += os.popen(args).read()
            return output
        else:
            return False

    def kazoo_command(self, command, path):
        from kazoo.client import KazooClient
        zk = KazooClient(hosts=self.get('zk'))
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

    def zk_command(self, command, path):
        result = ''
        if os.path.isfile(os.path.dirname(__file__) + '/zktool_linux_amd64'):
            result = self.zktool_command(command, path)
        if result:
            return result
        return self.kazoo_command(command, path)

    def zk_api_url(self):
        path = '/riak/frameworks/' + self.get('framework-name') + '/uri'
        url = self.zk_command('get', path)
        if url:
            return url.strip() + '/'
        return False

    def marathon_api_url(self):
        try:
            client = create_client(self.get_any('marathon', 'url'))
            tasks = client.get_tasks(self.get('framework-name'))
            if len(tasks) != 0:
                host = tasks[0]['host']
                port = tasks[0]['ports'][0]
                return 'http://' + host + ':' + str(port) + '/'
            return False
        except:
            return False

    def dcos_api_url(self):
        if not is_dcos():
            return False
        try:
            from dcos import util
            framework = self.get('framework-name')
            client = create_client(self.get_any('marathon', 'url'))
            tasks = client.get_tasks(self.get('framework-name'))
            if len(tasks) == 0:
                usage()
                raise CliError('Riak Mesos Framework is not running.')
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
            raise CliError(error)
        except Exception as e:
            raise CliError('Unable to find api url: ' + e.message)

    def default_framework_config(self):
        download_base = 'http://riak-tools.s3.amazonaws.com'
        download_base += '/riak-mesos/erlang/mesos-0.26/ubuntu/'
        riak_pkg = 'riak_mesos_linux_amd64_0.3.1.tar.gz'
        director_pkg = 'riak_mesos_director_linux_amd64_0.3.0.tar.gz'
        riak_url = download_base + riak_pkg
        director_url = download_base + director_pkg
        return {
            'riak': {
                'master': 'zk://leader.mesos:2181/mesos',
                'zk': 'leader.mesos:2181',
                'ip': '',
                'hostname': 'riak.mesos',
                'log': '',
                'user': 'ubuntu',
                'framework-name': 'riak',
                'role': 'riak',
                'url': riak_url,
                'auth-provider': '',
                'auth-principal': 'riak',
                'auth-secret-file': '',
                'instances': 1,
                'cpus': 0.5,
                'mem': 2048,
                'node': {
                    'cpus': 1.0,
                    'mem': 8000,
                    'disk': 20000
                },
                'flags': '-use_reservations',
                'super-chroot': 'true',
                'healthcheck-grace-period-seconds': 300,
                'healthcheck-interval-seconds': 60,
                'healthcheck-timeout-seconds': 20,
                'healthcheck-max-consecutive-failures': 5
            },
            'director': {
                'url': director_url,
                'cmd': './director/bin/ermf-director',
                'use-public': False
            },
            'marathon': {
                'url': 'http://marathon.mesos:8080'
            }
        }

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
