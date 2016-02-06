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

import utils


def config(cfg):
    if cfg.json_flag:
        print(config.string())
    else:
        ppobj('Framework: ', config.string(), 'riak', '[]')
        ppobj('Director: ', config.string(), 'director', '[]')
        ppobj('Marathon: ', config.string(), 'marathon', '[]')
    
        if case('framework config', 'framework'):
            obj = config.framework_marathon_string()
            if json_flag:
                print(obj)
            else:
                ppobj('Marathon Config: ', obj, '', '{}')
            break
        if case('framework uninstall'):
            print('Uninstalling framework...')
            fn = config.get('framework-name')
            client = create_client(config.get_any('marathon', 'url'))
            client.remove_app('/' + fn)
            print('Finished removing ' + '/' + fn + ' from marathon')
            break
        if case('framework clean-metadata'):
            fn = config.get('framework-name')
            print('\nRemoving zookeeper information\n')
            result = config.zk_command('delete', '/riak/frameworks/' + fn)
            if result:
                print(result)
            else:
                print("Unable to remove framework zookeeper data.")
            break
        if case('framework teardown'):
            r = requests.get('http://leader.mesos:5050/master/state.json')
            debug_request(debug_flag, r)
            if r.status_code != 200:
                print('Failed to get state.json from master.')
                break
            js = json.loads(r.text)
            for fw in js['frameworks']:
                if fw['name'] == config.get('framework-name'):
                    r = requests.post(
                        'http://leader.mesos:5050/master/teardown',
                        data='frameworkId='+fw['id'])
                    debug_request(debug_flag, r)
                    print('Finished teardown.')
            break
        if case('proxy config', 'proxy'):
            print(config.director_marathon_string(cluster))
            break
        if case('proxy install'):
            director_json = config.director_marathon_json(cluster)
            client = create_client(config.get_any('marathon', 'url'))
            client.add_app(director_json)
            print('Finished adding ' + director_json['id'] + ' to marathon.')
            break
        if case('proxy uninstall'):
            client = create_client(config.get_any('marathon', 'url'))
            fn = config.get('framework-name')
            client.remove_app('/' + fn + '-director')
            print('Finished removing ' + '/' + fn + '-director' +
                  ' from marathon')
            break
        if case('proxy endpoints'):
            client = create_client(config.get_any('marathon', 'url'))
            app = client.get_app(config.get('framework-name') + '-director')
            task = app['tasks'][0]
            ports = task['ports']
            hostname = task['host']
            print('Load Balanced Riak Cluster (HTTP)')
            print('    http://' + hostname + ':' + str(ports[0]))
            print('Load Balanced Riak Cluster (Protobuf)')
            print('    http://' + hostname + ':' + str(ports[1]))
            print('Riak Mesos Director API (HTTP)')
            print('    http://' + hostname + ':' + str(ports[2]))
            break
        if case('framework install'):
            framework_json = config.framework_marathon_json()
            client = create_client(config.get_any('marathon', 'url'))
            client.add_app(framework_json)
            print('Finished adding ' + framework_json['id'] + ' to marathon.')
            break
        if case('framework wait-for-service'):
            if wait_for_framework(config, debug_flag, 60):
                print('Riak Mesos Framework is ready.')
                break
            print('Riak Mesos Framework did not respond within 60 seconds.')
            break
        if case('node wait-for-service'):
            if node == '':
                raise utils.CliError('Node name must be specified')
            wait_for_node(config, cluster, debug_flag, node, 20)
            break
        if case('cluster wait-for-service'):
            if wait_for_framework(config, debug_flag, 60):
                service_url = config.api_url()
                r = requests.get(service_url + 'clusters/' + cluster +
                                 '/nodes')
                debug_request(debug_flag, r)
                js = json.loads(r.text)
                for k in js.keys():
                    wait_for_node(config, cluster, debug_flag, k, 20)
                break
            print('Riak Mesos Framework did not respond within 60 '
                  'seconds.')
            break
        if case('cluster endpoints'):
            if wait_for_framework(config, debug_flag, 60):
                service_url = config.api_url()
                r = requests.get(service_url + 'clusters/' + cluster +
                                 '/nodes')
                debug_request(debug_flag, r)
                if r.status_code == 200:
                    js = json.loads(r.text)
                    cluster_data = {}
                    for k in js.keys():
                        cluster_data[k] = node_info(config, cluster,
                                                    debug_flag, k)
                    print(json.dumps(cluster_data))
                else:
                    print(r.text)
                break
            print('Riak Mesos Framework did not respond within 60 '
                  'seconds.')
            break
        if case('proxy wait-for-service'):
            if wait_for_framework(config, debug_flag, 60):
                client = create_client(config.get_any('marathon', 'url'))
                app = client.get_app(config.get('framework-name') +
                                     '-director')
                if len(app['tasks']) == 0:
                    print("Proxy is not installed.")
                    break
                task = app['tasks'][0]
                ports = task['ports']
                hostname = task['host']
                if wait_for_url('http://' + hostname + ':' +
                                str(ports[0]), debug_flag, 20):
                    print("Proxy is ready.")
                    break
                print("Proxy did not respond in 20 seconds.")
                break
            print('Riak Mesos Framework did not respond within 60 seconds.')
            break
        if case('framework endpoints'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            print("Framework HTTP API: " + service_url)
            break
        if case('cluster config'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            if riak_file == '':
                r = requests.get(service_url + 'clusters/' + cluster)
                debug_request(debug_flag, r)
                if r.status_code == 200:
                    ppfact('riak.conf: ', r.text, 'RiakConfig',
                           'Error getting cluster.')
                else:
                    print('Cluster not created.')
                break
            with open(riak_file) as data_file:
                r = requests.post(service_url + 'clusters/' + cluster +
                                  '/config', data=data_file)
                debug_request(debug_flag, r)
                if r.status_code != 200:
                    print('Failed to set riak.conf, status_code: ' +
                          str(r.status_code))
                else:
                    print('riak.conf updated')
            break
        if case('cluster config advanced'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            if riak_file == '':
                r = requests.get(service_url + 'clusters/' + cluster)
                debug_request(debug_flag, r)
                if r.status_code == 200:
                    ppfact('advanced.config: ', r.text, 'AdvancedConfig',
                           'Error getting cluster.')
                else:
                    print('Cluster not created.')
                break
            with open(riak_file) as data_file:
                r = requests.post(service_url + 'clusters/' + cluster +
                                  '/advancedConfig', data=data_file)
                debug_request(debug_flag, r)
                if r.status_code != 200:
                    print('Failed to set advanced.config, status_code: ' +
                          str(r.status_code))
                else:
                    print('advanced.config updated')
            break
        if case('cluster list', 'cluster'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            r = requests.get(service_url + 'clusters')
            debug_request(debug_flag, r)
            if r.status_code == 200:
                if json_flag:
                    print(r.text)
                else:
                    pparr('Clusters: ', r.text, '[]')
            else:
                print('No clusters created')
            break
        if case('cluster create'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            r = requests.post(service_url + 'clusters/' + cluster, data='')
            debug_request(debug_flag, r)
            if r.text == '' or r.status_code != 200:
                print('Cluster already exists.')
            else:
                ppfact('Added cluster: ', r.text, 'Name',
                       'Error creating cluster.')
            break
        if case('cluster restart'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            r = requests.post(service_url + 'clusters/' + cluster + '/restart',
                              data='')
            debug_request(debug_flag, r)
            if r.status_code == 404:
                print('Cluster does not exist.')
            elif r.status_code != 202:
                print('Failed to restart cluster, status code: ' +
                      str(r.status_code))
            else:
                print('Cluster restart initiated.')
            break
        if case('cluster destroy'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            r = requests.delete(service_url + 'clusters/' + cluster, data='')
            debug_request(debug_flag, r)
            if r.status_code != 202:
                print('Failed to destroy cluster, status_code: ' +
                      str(r.status_code))
            else:
                print('Destroyed cluster: ' + cluster)
            break
        if case('node list', 'node'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            r = requests.get(service_url + 'clusters/' + cluster + '/nodes')
            debug_request(debug_flag, r)
            if json_flag:
                print(r.text)
            else:
                pparr('Nodes: ', r.text, '[]')
            break
        if case('node info'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            r = requests.get(service_url + 'clusters/' + cluster + '/nodes')
            debug_request(debug_flag, r)
            node_json = json.loads(r.text)
            print('HTTP: http://' + node_json[node]['Hostname'] + ':' +
                  str(node_json[node]['TaskData']['HTTPPort']))
            print('PB  : ' + node_json[node]['Hostname'] + ':' +
                  str(node_json[node]['TaskData']['PBPort']))
            ppobj('Node: ', r.text, node, '{}')
            break
        if case('node add'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            for x in range(0, num_nodes):
                r = requests.post(service_url + 'clusters/' + cluster +
                                  '/nodes', data='')
                debug_request(debug_flag, r)
                if r.status_code != 200:
                    print(r.text)
                else:
                    ppfact('New node: ' + config.get('framework-name') + '-' +
                           cluster + '-', r.text, 'SimpleId', 'Error adding '
                           'node')
            break
        if case('node remove'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            if node == '':
                raise CliError('Node name must be specified')
            r = requests.delete(service_url + 'clusters/' + cluster +
                                '/nodes/' + node, data='')
            debug_request(debug_flag, r)
            if r.status_code != 202:
                print('Failed to remove node, status_code: ' +
                      str(r.status_code))
            else:
                print('Removed node')
            break
        if case('node aae-status'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            if node == '':
                raise CliError('Node name must be specified')
            r = requests.get(service_url + 'clusters/' + cluster + '/nodes/' +
                             node + '/aae')
            debug_request(debug_flag, r)
            if r.status_code != 200:
                print('Failed to get aae-status, status_code: ' +
                      str(r.status_code))
            else:
                ppobj('', r.text, 'aae-status', '{}')
            break
        if case('node status'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            if node == '':
                raise CliError('Node name must be specified')
            r = requests.get(service_url + 'clusters/' + cluster + '/nodes/' +
                             node + '/status')
            debug_request(debug_flag, r)
            if r.status_code != 200:
                print('Failed to get status, status_code: ' +
                      str(r.status_code))
            else:
                ppobj('', r.text, 'status', '{}')
            break
        if case('node ringready'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            if node == '':
                raise CliError('Node name must be specified')
            r = requests.get(service_url + 'clusters/' + cluster + '/nodes/' +
                             node + '/ringready')
            debug_request(debug_flag, r)
            if r.status_code != 200:
                print('Failed to get ringready, status_code: ' +
                      str(r.status_code))
            else:
                ppobj('', r.text, 'ringready', '{}')
            break
        if case('node transfers'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            if node == '':
                raise CliError('Node name must be specified')
            r = requests.get(service_url + 'clusters/' + cluster + '/nodes/' +
                             node + '/transfers')
            debug_request(debug_flag, r)
            if r.status_code != 200:
                print('Failed to get transfers, status_code: ' +
                      str(r.status_code))
            else:
                ppobj('', r.text, 'transfers', '{}')
            break
        if case('node bucket-type create'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            if node == '' or bucket_type == '' or props == '':
                raise CliError('Node name, bucket-type, props must be '
                               'specified')
            r = requests.post(service_url + 'clusters/' + cluster + '/nodes/' +
                              node + '/types/' + bucket_type, data=props)
            debug_request(debug_flag, r)
            if r.status_code != 200:
                print('Failed to create bucket-type, status_code: ' +
                      str(r.status_code))
                ppobj('', r.text, '', '{}')
            else:
                ppobj('', r.text, '', '{}')
            break
        if case('node bucket-type list'):
            service_url = config.api_url()
            if service_url is False:
                raise CliError("Riak Mesos Framework is not running.")
            if node == '':
                raise CliError('Node name must be specified')
            r = requests.get(service_url + 'clusters/' + cluster + '/nodes/' +
                             node + '/types')
            debug_request(debug_flag, r)
            if r.status_code != 200:
                print('Failed to get bucket types, status_code: ' +
                      str(r.status_code))
            else:
                ppobj('', r.text, 'bucket_types', '{}')
            break
        if case():
            raise CliError('Unrecognized command: ' + cmd)
    return 0
