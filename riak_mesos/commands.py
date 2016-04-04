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
from riak_mesos import util
from riak_mesos.util import CliError


def config(args, cfg):
    print(cfg.string())


def framework(args, cfg):
    framework_config(args, cfg)


def framework_config(args, cfg):
    obj = cfg.framework_marathon_string()
    print(obj)
    return


def framework_install(args, cfg):
    framework_json = cfg.framework_marathon_json()
    client = util.marathon_client(cfg.get('marathon'))
    client.add_app(framework_json)
    print('Finished adding ' + framework_json['id'] + ' to marathon.')
    return


def framework_status(args, cfg):
    client = util.marathon_client(cfg.get('marathon'))
    result = client.get_app('/' + cfg.get('framework-name'))
    print(json.dumps(result))


def framework_wait_for_service(args, cfg):
    if util.wait_for_framework(cfg, args['debug_flag'], 60):
        print('Riak Mesos Framework is ready.')
        return
    print('Riak Mesos Framework did not respond within 60 seconds.')
    return


def framework_uninstall(args, cfg):
    print('Uninstalling framework...')
    client = util.marathon_client(cfg.get('marathon'))
    client.remove_app('/' + cfg.get('framework-name'))
    print('Finished removing ' + '/' + cfg.get('framework-name') +
          ' from marathon')
    return


def framework_clean_metadata(args, cfg):
    fn = cfg.get('framework-name')
    print('\nRemoving zookeeper information\n')
    result = util.zookeeper_command(cfg.get('zk'), 'delete',
                                    '/riak/frameworks/' + fn)
    if result:
        print(result)
    else:
        print("Unable to remove framework zookeeper data.")
    return


def framework_teardown(args, cfg):
    r = requests.get('http://' + cfg.get('master') + '/master/state.json')
    util.debug_request(args['debug_flag'], r)
    if r.status_code != 200:
        print('Failed to get state.json from master.')
        return
    js = json.loads(r.text)
    for fw in js['frameworks']:
        if fw['name'] == cfg.get('framework-name'):
            r = requests.post(
                'http://' + cfg.get('master') + '/master/teardown',
                data='frameworkId='+fw['id'])
            util.debug_request(args['debug_flag'], r)
            print('Finished teardown.')
    return


def director_config(args, cfg):
    director(args, cfg)


def director(args, cfg):
    print(cfg.director_marathon_string(args['cluster']))
    return


def director_wait_for_service(args, cfg):
    if util.wait_for_framework(cfg, args['debug_flag'], 60):
        client = util.marathon_client(cfg.get('marathon'))
        app = client.get_app(cfg.get('framework-name') +
                             '-director')
        if len(app['tasks']) == 0:
            print("Director is not installed.")
            return
        task = app['tasks'][0]
        ports = task['ports']
        hostname = task['host']
        if util.wait_for_url('http://' + hostname + ':' +
                             str(ports[0]), args['debug_flag'], 20):
            print("Director is ready.")
            return
        print("Director did not respond in 20 seconds.")
        return
    print('Riak Mesos Framework did not respond within 60 seconds.')
    return


def director_install(args, cfg):
    director_json = cfg.director_marathon_json(args['cluster'])
    client = util.marathon_client(cfg.get('marathon'))
    client.add_app(director_json)
    print('Finished adding ' + director_json['id'] + ' to marathon.')
    return


def director_uninstall(args, cfg):
    client = util.marathon_client(cfg.get('marathon'))
    client.remove_app('/' + args['cluster'] + '-director')
    print('Finished removing ' + '/' + args['cluster'] + '-director' +
          ' from marathon')
    return


def director_endpoints(args, cfg):
    client = util.marathon_client(cfg.get('marathon'))
    app = client.get_app('/' + args['cluster'] + '-director')
    task = app['tasks'][0]
    ports = task['ports']
    hostname = task['host']
    endpoints = {
        'framework': cfg.get('framework-name'),
        'cluster': args['cluster'],
        'riak_http': hostname + ':' + str(ports[0]),
        'riak_pb': hostname + ':' + str(ports[1]),
        'director_http': hostname + ':' + str(ports[2])
    }
    print(json.dumps(endpoints))
    return


def proxy_wait_for_service(args, cfg):
    director_wait_for_service(args, cfg)


def proxy_config(args, cfg):
    director(args, cfg)


def proxy(args, cfg):
    director(args, cfg)


def proxy_install(args, cfg):
    director_install(args, cfg)


def proxy_uninstall(args, cfg):
    director_uninstall(args, cfg)


def proxy_endpoints(args, cfg):
    director_endpoints(args, cfg)


def node_wait_for_service(args, cfg):
    if args['node'] == '':
        raise CliError('Node name must be specified')
    util.wait_for_node(cfg, args['cluster'], args['debug_flag'],
                       args['node'], 20)
    return


def cluster_wait_for_service(args, cfg):
    if util.wait_for_framework(cfg, args['debug_flag'], 60):
        service_url = cfg.api_url()
        r = requests.get(service_url + 'clusters/' + args['cluster'] +
                         '/nodes')
        util.debug_request(args['debug_flag'], r)
        js = json.loads(r.text)
        for k in js['nodes']:
            util.wait_for_node(cfg, args['cluster'], args['debug_flag'],
                               k, 20)
        return
    print('Riak Mesos Framework did not respond within 60 '
          'seconds.')
    return


def cluster_endpoints(args, cfg):
    if util.wait_for_framework(cfg, args['debug_flag'], 60):
        service_url = cfg.api_url()
        r = requests.get(service_url + 'clusters/' + args['cluster'] +
                         '/nodes')
        util.debug_request(args['debug_flag'], r)
        cluster_data = {}
        if r.status_code == 200:
            js = json.loads(r.text)
            for k in js["nodes"]:
                cluster_data[k] = util.node_info(cfg, args['cluster'],
                                                 args['debug_flag'], k)
            print(json.dumps(cluster_data))
            return
        else:
            print(r.text)
            return
    print('Riak Mesos Framework did not respond within 60 '
          'seconds.')
    return


def framework_endpoints(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    print("Framework HTTP API: " + service_url)
    return


def cluster_info(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")

    r = requests.get(service_url + 'clusters/' + args['cluster'])
    util.debug_request(args['debug_flag'], r)
    print(r.text)
    return


def cluster_config(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    if args['riak_file'] == '':
        r = requests.get(service_url + 'clusters/' + args['cluster'] +
                         '/config')
        util.debug_request(args['debug_flag'], r)
        print(r.text)
    else:
        with open(args['riak_file']) as data_file:
            r = requests.post(service_url + 'clusters/' + args['cluster'] +
                              '/cfg', data=data_file)
            util.debug_request(args['debug_flag'], r)
            print(r.text)
    return


def cluster_config_advanced(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    if args['riak_file'] == '':
        r = requests.get(service_url + 'clusters/' + args['cluster'] +
                         '/advancedConfig')
        util.debug_request(args['debug_flag'], r)
        print(r.text)
    else:
        with open(args['riak_file']) as data_file:
            r = requests.post(service_url + 'clusters/' + args['cluster'] +
                              '/advancedCfg', data=data_file)
            util.debug_request(args['debug_flag'], r)
            print(r.text)
    return


def cluster_list(args, cfg):
    cluster(args, cfg)


def cluster(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    r = requests.get(service_url + 'clusters')
    util.debug_request(args['debug_flag'], r)
    print(r.text)
    return


def cluster_create(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    r = requests.put(service_url + 'clusters/' + args['cluster'], data='')
    util.debug_request(args['debug_flag'], r)
    print(r.text)
    return


def cluster_restart(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    r = requests.post(service_url + 'clusters/' + args['cluster'] + '/restart',
                      data='')
    util.debug_request(args['debug_flag'], r)
    print(r.text)
    return


def cluster_destroy(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    r = requests.delete(service_url + 'clusters/' + args['cluster'], data='')
    util.debug_request(args['debug_flag'], r)
    print(r.text)
    return


def node_list(args, cfg):
    node(args, cfg)


def node(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    r = requests.get(service_url + 'clusters/' + args['cluster'] + '/nodes')
    util.debug_request(args['debug_flag'], r)
    print(r.text)
    return


def node_info(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    r = requests.get(service_url + 'clusters/' + args['cluster'] + '/nodes/' +
                     args['node'])
    util.debug_request(args['debug_flag'], r)
    # TODO: Parse the relevant parts of the node info
    print(r.text)
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


def node_add(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    for x in range(0, args['num_nodes']):
        r = requests.post(service_url + 'clusters/' + args['cluster'] +
                          '/nodes', data='')
        util.debug_request(args['debug_flag'], r)
        print(r.text)
    return


def node_remove(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    if args['node'] == '':
        raise CliError('Node name must be specified')
    requrl = service_url + 'clusters/'
    requrl += args['cluster'] + '/nodes/' + args['node']
    if args['force_flag']:
        requrl += '?force=true'
    r = requests.delete(requrl, data='')
    util.debug_request(args['debug_flag'], r)
    print(r.text)
    return


# TODO Maybe just proxy the riak explorer commands straight to nodes
def node_aae_status(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    if args['node'] == '':
        raise CliError('Node name must be specified')
    r = requests.get(service_url + 'clusters/' + args['cluster'] + '/nodes/' +
                     args['node'] + '/aae')
    util.debug_request(args['debug_flag'], r)
    print(r.text)
    return


def node_status(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    if args['node'] == '':
        raise CliError('Node name must be specified')
    r = requests.get(service_url + 'clusters/' + args['cluster'] + '/nodes/' +
                     args['node'] + '/status')
    util.debug_request(args['debug_flag'], r)
    print(r.text)
    return


def node_ringready(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    if args['node'] == '':
        raise CliError('Node name must be specified')
    r = requests.get(service_url + 'clusters/' + args['cluster'] + '/nodes/' +
                     args['node'] + '/ringready')
    util.debug_request(args['debug_flag'], r)
    print(r.text)
    return


def node_transfers(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    if args['node'] == '':
        raise CliError('Node name must be specified')
    r = requests.get(service_url + 'clusters/' + args['cluster'] + '/nodes/' +
                     args['node'] + '/transfers')
    util.debug_request(args['debug_flag'], r)
    print(r.text)
    return


def node_bucket_type_create(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    if args['node'] == '' or args['bucket_type'] == '' or args['props'] == '':
        raise CliError('Node name, bucket-type, props must be '
                       'specified')
    r = requests.post(service_url + 'clusters/' + args['cluster'] + '/nodes/' +
                      args['node'] + '/types/' + args['bucket_type'],
                      data=args['props'])
    util.debug_request(args['debug_flag'], r)
    print(r.text)
    return


def node_bucket_type_list(args, cfg):
    service_url = cfg.api_url()
    if service_url is False:
        raise CliError("Riak Mesos Framework is not running.")
    if args['node'] == '':
        raise CliError('Node name must be specified')
    r = requests.get(service_url + 'clusters/' + args['cluster'] + '/nodes/' +
                     args['node'] + '/types')
    util.debug_request(args['debug_flag'], r)
    print(r.text)
    return


def try_json(data):
    try:
        return json.loads(data)
    except:
        return False
