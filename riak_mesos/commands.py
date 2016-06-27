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

from riak_mesos import util
from riak_mesos.util import CliError


def config(cfg):
    print(cfg.string())


def framework(cfg):
    framework_config(cfg)


def framework_config(cfg):
    obj = cfg.framework_marathon_string()
    print(obj)
    return


def framework_install(cfg):
    framework_json = cfg.framework_marathon_json()
    client = util.marathon_client(cfg.get('marathon'))
    client.add_app(framework_json)
    print('Finished adding ' + framework_json['id'] + ' to marathon.')
    return


def framework_status(cfg):
    client = util.marathon_client(cfg.get('marathon'))
    result = client.get_app('/' + cfg.get('framework-name'))
    print(json.dumps(result))


def framework_wait_for_service(cfg):
    if util.wait_for_framework(cfg):
        print('Riak Mesos Framework is ready.')
        return
    print('Riak Mesos Framework did not respond within ' +
          str(cfg.args['timeout']) + ' seconds.')
    return


def framework_uninstall(cfg):
    print('Uninstalling framework...')
    client = util.marathon_client(cfg.get('marathon'))
    client.remove_app('/' + cfg.get('framework-name'))
    print('Finished removing ' + '/' + cfg.get('framework-name') +
          ' from marathon')
    return


def framework_clean_metadata(cfg):
    fn = cfg.get('framework-name')
    if cfg.args['force_flag']:
        print('\nRemoving zookeeper information\n')
        result = util.zookeeper_command(cfg.get('zk'), 'delete',
                                        '/riak/frameworks/' + fn)
        if result:
            print(result)
        else:
            print("Unable to remove framework zookeeper data.")
    else:
        print('\nFramework metadata not removed. Use the --force flag to '
              'delete all framework zookeeper metadata.\n\n'
              'WARNING: Running this command with a running instance of the '
              'Riak Mesos Framework will cause unexpected behavior and '
              'possible data loss!\n')
    return


def framework_teardown(cfg):
    r = util.http_request('get', 'http://' + cfg.get('master') +
                          '/master/state.json')
    util.debug_request(cfg.args['debug_flag'], r)
    if r.status_code != 200:
        print('Failed to get state.json from master.')
        return
    js = json.loads(r.text)
    for fw in js['frameworks']:
        if fw['name'] == cfg.get('framework-name'):
            r = util.http_request('post',
                                  'http://' + cfg.get('master') +
                                  '/master/teardown',
                                  data='frameworkId='+fw['id'])
            util.debug_request(cfg.args['debug_flag'], r)
            print('Finished teardown.')
    return


def director_config(cfg):
    director(cfg)


def director(cfg):
    print(cfg.director_marathon_string(cfg.args['cluster']))
    return


def director_wait_for_service(cfg):
    if util.wait_for_framework(cfg):
        util.wait_for_director(cfg)
        return
    print('Riak Mesos Framework did not respond within ' +
          str(cfg.args['timeout']) + 'seconds.')
    return


def director_install(cfg):
    director_json = cfg.director_marathon_json(cfg.args['cluster'])
    client = util.marathon_client(cfg.get('marathon'))
    client.add_app(director_json)
    print('Finished adding ' + director_json['id'] + ' to marathon.')
    return


def director_uninstall(cfg):
    client = util.marathon_client(cfg.get('marathon'))
    client.remove_app('/' + cfg.args['cluster'] + '-director')
    print('Finished removing ' + '/' + cfg.args['cluster'] + '-director' +
          ' from marathon')
    return


def director_endpoints(cfg):
    client = util.marathon_client(cfg.get('marathon'))
    app = client.get_app('/' + cfg.args['cluster'] + '-director')
    task = app['tasks'][0]
    ports = task['ports']
    hostname = task['host']
    endpoints = {
        'framework': cfg.get('framework-name'),
        'cluster': cfg.args['cluster'],
        'riak_http': hostname + ':' + str(ports[0]),
        'riak_pb': hostname + ':' + str(ports[1]),
        'director_http': hostname + ':' + str(ports[2])
    }
    print(json.dumps(endpoints))
    return


def proxy_wait_for_service(cfg):
    director_wait_for_service(cfg)


def proxy_config(cfg):
    director(cfg)


def proxy(cfg):
    director(cfg)


def proxy_install(cfg):
    director_install(cfg)


def proxy_uninstall(cfg):
    director_uninstall(cfg)


def proxy_endpoints(cfg):
    director_endpoints(cfg)


def cluster_wait_for_service(cfg):
    if util.wait_for_framework(cfg):
        r = util.api_request(cfg, 'get', 'clusters/' +
                             cfg.args['cluster'] + '/nodes')
        js = json.loads(r.text)
        # Timeout must be at least 1 second
        num_nodes = len(js['nodes'])
        total_timeout = cfg.args['timeout']
        if num_nodes > 0:
            cfg.args['timeout'] = max(total_timeout / num_nodes, 1)
            for k in js['nodes']:
                util.wait_for_node(cfg, k)
        if num_nodes >= cfg.args['num_nodes']:
            # Okay, need to divide up the timeout properly
            cfg.args['timeout'] = total_timeout
            util.wait_for_node_status_valid(cfg, js['nodes'][0])
        return
    print('Riak Mesos Framework did not respond within ' +
          str(cfg.args['timeout']) + 'seconds.')
    return


def cluster_endpoints(cfg):
    if util.wait_for_framework(cfg):
        r = util.api_request(cfg, 'get', 'clusters/' +
                             cfg.args['cluster'] + '/nodes')
        cluster_data = {}
        if r.status_code == 200:
            js = json.loads(r.text)
            for k in js["nodes"]:
                cluster_data[k] = util.node_info(cfg, k)
            print(json.dumps(cluster_data))
            return
        else:
            print(r.text)
            return
    print('Riak Mesos Framework did not respond within ' +
          str(cfg.args['timeout']) + 'seconds.')
    return


def framework_endpoints(cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    print("Framework HTTP API: " + service_url)
    return


def cluster_info(cfg):
    r = util.api_request(cfg, 'get', 'clusters/' + cfg.args['cluster'])
    print(r.text)
    return


def cluster_config(cfg):
    if cfg.args['riak_file'] == '':
        r = util.api_request(cfg, 'get', 'clusters/' +
                             cfg.args['cluster'] + '/config')
        print(r.text)
    else:
        with open(cfg.args['riak_file']) as data_file:
            r = util.api_request(cfg, 'put', 'clusters/' +
                                 cfg.args['cluster'] + '/config',
                                 data=data_file)
            print(r.text)
    return


def cluster_config_advanced(cfg):
    if cfg.args['riak_file'] == '':
        r = util.api_request(cfg, 'get', 'clusters/' +
                             cfg.args['cluster'] + '/advancedConfig')
        print(r.text)
    else:
        with open(cfg.args['riak_file']) as data_file:
            r = util.api_request(cfg, 'put', 'clusters/' +
                                 cfg.args['cluster'] + '/advancedConfig',
                                 data=data_file)
            print(r.text)
    return


def cluster_list(cfg):
    cluster(cfg)


def cluster(cfg):
    r = util.api_request(cfg, 'get', 'clusters')
    print(r.text)
    return


def cluster_create(cfg):
    r = util.api_request(cfg, 'put', 'clusters/' + cfg.args['cluster'],
                         data='')
    print(r.text)
    return


def cluster_restart(cfg):
    r = util.api_request(cfg, 'post', 'clusters/' + cfg.args['cluster'] +
                         '/restart', data='')
    print(r.text)
    return


def cluster_destroy(cfg):
    r = util.api_request(cfg, 'delete', 'clusters/' +
                         cfg.args['cluster'], data='')
    print(r.text)
    return


def node_wait_for_service(cfg):
    if cfg.args['node'] == '':
        raise CliError('Node name must be specified')
    util.wait_for_node(cfg, cfg.args['node'])
    return


def node_list(cfg):
    node(cfg)


def node(cfg):
    r = util.api_request(cfg, 'get', 'clusters/' + cfg.args['cluster'] +
                         '/nodes')
    print(r.text)
    return


def node_info(cfg):
    r = util.api_request(cfg, 'get', 'clusters/' +
                         cfg.args['cluster'] + '/nodes/' + cfg.args['node'])
    print(r.text)
    # TODO: Parse the relevant parts of the node info
    # node_json = try_json(r.text)
    # if (node_json is not False):
    #     print('HTTP: http://' + node_json[node]['Hostname'] + ':' +
    #           str(node_json[node]['TaskData']['HTTPPort']))
    #     print('PB  : ' + node_json[node]['Hostname'] + ':' +
    #           str(node_json[node]['TaskData']['PBPort']))
    #     util.ppobj('Node: ', r.text, node, '{}')
    # else:
    #     print(r.text)
    return


def node_add(cfg):
    for x in range(0, cfg.args['num_nodes']):
        r = util.api_request(cfg, 'post', 'clusters/' +
                             cfg.args['cluster'] + '/nodes', data='')
        print(r.text)
    return


def node_remove(cfg):
    if cfg.args['node'] == '':
        raise CliError('Node name must be specified')
    requrl = 'clusters/'
    requrl += cfg.args['cluster'] + '/nodes/' + cfg.args['node']
    if cfg.args['force_flag']:
        requrl += '?force=true'
    r = util.api_request(cfg, 'delete',  requrl, data='')
    print(r.text)
    return


# TODO Maybe just proxy the riak explorer commands straight to nodes
def node_aae_status(cfg):
    if cfg.args['node'] == '':
        raise CliError('Node name must be specified')
    r = util.api_request(cfg, 'get', 'clusters/' + cfg.args['cluster'] +
                         '/nodes/' + cfg.args['node'] + '/aae')
    print(r.text)
    return


def node_status(cfg):
    if cfg.args['node'] == '':
        raise CliError('Node name must be specified')
    r = util.api_request(cfg, 'get', 'clusters/' + cfg.args['cluster'] +
                         '/nodes/' + cfg.args['node'] + '/status')
    print(r.text)
    return


def node_ringready(cfg):
    if cfg.args['node'] == '':
        raise CliError('Node name must be specified')
    r = util.api_request(cfg, 'get', 'clusters/' + cfg.args['cluster'] +
                         '/nodes/' + cfg.args['node'] + '/ringready')
    print(r.text)
    return


def node_transfers(cfg):
    if cfg.args['node'] == '':
        raise CliError('Node name must be specified')
    r = util.api_request(cfg, 'get', 'clusters/' + cfg.args['cluster'] +
                         '/nodes/' + cfg.args['node'] + '/transfers')
    print(r.text)
    return


def node_transfers_wait_for_service(cfg):
    if cfg.args['node'] == '':
        raise CliError('Node name must be specified')
    util.wait_for_node_transfers(cfg, cfg.args['node'])
    return


def node_bucket_type_create(cfg):
    if cfg.args['node'] == '':
        raise CliError('Node name must be specified')
    if cfg.args['bucket_type'] == '':
        raise CliError('Bucket-Type must be specified')
    if cfg.args['props'] == '':
        raise CliError('Props must be specified')
    r = util.api_request(cfg, 'post', 'clusters/' + cfg.args['cluster'] +
                         '/nodes/' + cfg.args['node'] +
                         '/types/' + cfg.args['bucket_type'],
                         data=cfg.args['props'])
    print(r.text)
    return


def node_bucket_type_list(cfg):
    if cfg.args['node'] == '':
        raise CliError('Node name must be specified')
    r = util.api_request(cfg, 'get', 'clusters/' + cfg.args['cluster'] +
                         '/nodes/' + cfg.args['node'] + '/types')
    print(r.text)
    return


def try_json(data):
    try:
        return json.loads(data)
    except:
        return False


def node_log_list(cfg):
    if cfg.args['node'] == '':
        raise CliError('Node name must be specified')
    node_name = util.get_node_name(cfg, cfg.args['node'])
    r = util.api_request(cfg, 'get', 'explore/clusters/' +
                         cfg.args['cluster'] + '/nodes/' +
                         node_name + '/log/files')
    if r.status_code != 200:
        print('Failed to get log files, status_code: ' +
              str(r.status_code))
    else:
        print(r.text)
    return


def node_log(cfg):
    if cfg.args['node'] == '':
        raise CliError('Node name must be specified')
    if cfg.args['riak_file'] == '':
        raise CliError('Log file must be specified')
    node_name = util.get_node_name(cfg, cfg.args['node'])
    r = util.api_request(cfg, 'get', 'explore/clusters/' +
                         cfg.args['cluster'] + '/nodes/' +
                         node_name + '/log/files/' +
                         cfg.args['riak_file'] + '?rows=' +
                         cfg.args['lines'])
    if r.status_code != 200:
        print('Failed to get log files, status_code: ' +
              str(r.status_code))
    else:
        print(r.text)
    return


def node_stats(cfg):
    if cfg.args['node'] == '':
        raise CliError('Node name must be specified')
    r = util.api_request(cfg, 'get', 'riak/nodes/' +
                         cfg.args['node'] + '/stats')
    if r.status_code != 200:
        print('Failed to get stats, status_code: ' +
              str(r.status_code))
    else:
        print(r.text)
    return
