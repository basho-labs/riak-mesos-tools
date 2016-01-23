import json
import requests


def _to_exception(response):
    if response is None:
        return Exception("Unable to get valid response.")
    if response.status_code == 400:
        msg = 'Error on request [{0} {1}]: HTTP {2}: {3}'.format(
            response.request.method,
            response.request.url,
            response.status_code,
            response.reason)
        try:
            json_msg = response.json()
            msg += ':\n' + json.dumps(json_msg,
                                      indent=2,
                                      sort_keys=True,
                                      separators=(',', ': '))
        except ValueError:
            pass
        return Exception(msg)
    elif response.status_code == 409:
        return Exception(
            'App or group is locked by one or more deployments. '
            'Override with --force.')
    try:
        response_json = response.json()
    except Exception as ex:
        return ex
    message = response_json.get('message')
    if message is None:
        errs = response_json.get('errors')
        if errs is None:
            return Exception('Marathon likely misconfigured.')

        msg = '\n'.join(error['error'] for error in errs)
        return Exception('Marathon likely misconfigured.')
    return Exception('Error: {}'.format(message))


def _http_req(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except requests.exceptions.ConnectionError as e:
        raise e
    except requests.exceptions.RequestException as e:
        raise _to_exception(e.response)


# Marathon
class Client(object):
    def __init__(self, marathon_url, timeout=6000):
        self._base_url = marathon_url
        self._timeout = timeout

    def normalize_app_id(self, app_id):
        return '/' + app_id.strip('/')

    def _create_url(self, path):
        return self._base_url + '/' + path

    def get_app(self, app_id):
        app_id = self.normalize_app_id(app_id)
        url = self._create_url('v2/apps{}'.format(app_id))
        response = _http_req(requests.get, url, timeout=self._timeout)
        return response.json()['app']

    def get_apps(self):
        url = self._create_url('v2/apps')
        response = _http_req(requests.get, url, timeout=self._timeout)
        return response.json()['apps']

    def add_app(self, app_resource):
        url = self._create_url('v2/apps')
        if hasattr(app_resource, 'read'):
            app_json = json.load(app_resource)
        else:
            app_json = app_resource
        response = _http_req(requests.post, url,
                             data=json.dumps(app_json),
                             timeout=self._timeout)
        return response.json()

    def scale_app(self, app_id, instances, force=None):
        app_id = self.normalize_app_id(app_id)
        if not force:
            params = None
        else:
            params = {'force': 'true'}
        url = self._create_url('v2/apps{}'.format(app_id))
        response = _http_req(requests.put,
                             url,
                             params=params,
                             data=json.dumps({'instances': int(instances)}),
                             timeout=self._timeout)
        deployment = response.json()['deploymentId']
        return deployment

    def stop_app(self, app_id, force=None):
        return self.scale_app(app_id, 0, force)

    def remove_app(self, app_id, force=None):
        app_id = self.normalize_app_id(app_id)
        if not force:
            params = None
        else:
            params = {'force': 'true'}
        url = self._create_url('v2/apps{}'.format(app_id))
        _http_req(requests.delete, url, params=params, timeout=self._timeout)

    def restart_app(self, app_id, force=None):
        app_id = self.normalize_app_id(app_id)
        if not force:
            params = None
        else:
            params = {'force': 'true'}
        url = self._create_url('v2/apps{}/restart'.format(app_id))
        response = _http_req(requests.post, url,
                             params=params,
                             timeout=self._timeout)
        return response.json()

    def get_tasks(self, app_id):
        url = self._create_url('v2/tasks')
        response = _http_req(requests.get, url, timeout=self._timeout)
        if app_id is not None:
            app_id = self.normalize_app_id(app_id)
            tasks = [
                task for task in response.json()['tasks']
                if app_id == task['appId']
            ]
        else:
            tasks = response.json()['tasks']
        return tasks

    def get_task(self, task_id):
        url = self._create_url('v2/tasks')
        response = _http_req(requests.get, url, timeout=self._timeout)
        task = next(
            (task for task in response.json()['tasks']
             if task_id == task['id']),
            None)
        return task
