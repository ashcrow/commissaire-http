# Copyright (C) 2016  Red Hat, Inc
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Prototype dispatcher.
"""

import json
import logging
import traceback
import uuid

from importlib import import_module
from inspect import signature, isfunction, isclass

from commissaire_http.bus import Bus
from commissaire_http.constants import JSONRPC_ERRORS
from commissaire_http.handlers import parse_query_string


def ls_mod(mod, pkg):
    """
    Yields all non internal/protected attributes in a module.

    :param mod: The module itself.
    :type mod:
    :param pkg: The full package name.
    :type pkg: str
    :returns: Tuple of attribute name, attribute, attribute path.
    :rtype: tuple
    """
    for item in dir(mod):
        # Skip all protected and internals
        if not item.startswith('_'):
            attr = getattr(mod, item)
            mod_path = '.'.join([pkg, item])
            yield item, attr, mod_path


class DispatcherError(Exception):  # pragma: no cover
    """
    Dispatcher related errors.
    """
    pass


class Dispatcher:
    """
    Dispatches and translates between HTTP requests and bus services.
    """

    #: Logging instance for all Dispatchers
    logger = logging.getLogger('Dispatcher')

    def __init__(self, router, handler_packages):
        """
        Initializes a new Dispatcher instance.

        :param router: The router to dispatch with.
        :type router: router.TopicRouter
        :param handler_packages: List of packages to load handlers from.
        :type handler_packages: list
        """
        self._router = router
        self._handler_packages = handler_packages
        self._handler_map = {}
        self.reload_handlers()
        self._bus = None

    def setup_bus(self, exchange_name, connection_url, qkwargs):
        """
        Sets up a bus connection with the given configuration.

        Call this method only once after instantiating a Dispatcher.

        :param exchange_name: Name of the topic exchange
        :type exchange_name: str
        :param connection_url: Kombu connection URL
        :type connection_url: str
        :param qkwargs: One or more keyword argument dicts for queue creation
        :type qkwargs: list
        """
        self.logger.debug('Setting up bus connection.')
        bus_init_kwargs = {
            'exchange_name': exchange_name,
            'connection_url': connection_url,
            'qkwargs': qkwargs
        }
        self._bus = Bus(**bus_init_kwargs)
        self.logger.debug(
            'Bus instance created with: {}'.format(bus_init_kwargs))
        self._bus.connect()
        self.logger.info('Bus connection ready.')

    def reload_handlers(self):
        """
        Reloads the handler mapping.
        """
        for pkg in self._handler_packages:
            try:
                mod = import_module(pkg)
                for item, attr, mod_path in ls_mod(mod, pkg):
                    if isfunction(attr):
                        # Check that it has 2 inputs
                        if len(signature(attr).parameters) == 2:
                            self._handler_map[mod_path] = attr
                            self.logger.info(
                                'Loaded function handler {} to {}'.format(
                                    mod_path, attr))
                    elif isclass(attr) and issubclass(attr, object):
                        handler_instance = attr()
                        for handler_meth, sub_attr, sub_mod_path in \
                                ls_mod(handler_instance, pkg):
                            key = '.'.join([mod_path, handler_meth])
                            self._handler_map[key] = getattr(
                                handler_instance, handler_meth)
                            self.logger.info(
                                'Instansiated and loaded class handler '
                                '{} to {}'.format(key, handler_instance))
                    else:
                        self.logger.debug(
                            '{} can not be used as a handler.'.format(
                                mod_path))
            except ImportError as error:
                self.logger.error(
                    'Unable to import handler package "{}". {}: {}'.format(
                        pkg, type(error), error))

    def _get_params(self, environ, route, route_data):
        """
        Handles pulling parameters out of the various inputs.

        :param environ: WSGI environment dictionary.
        :type environ: dict
        :param route: The route structure returned by a routematch.
        :type route: dict
        :param route_data: Specific internals on a matched route.
        :type route_data: dict
        :returns: The found parameters.
        :rtype: dict
        """
        params = {}
        # Initial params come from the urllib
        for param_key in route_data.minkeys:
            params[param_key] = route[param_key]

        # If we are a PUT or POST look for params in wsgi.input
        if environ['REQUEST_METHOD'] in ('PUT', 'POST'):
            content_length = int(environ.get('CONTENT_LENGTH', 0))
            if content_length > 0:
                try:
                    wsgi_input = environ['wsgi.input'].read(content_length)
                    more_params = json.loads(wsgi_input.decode())
                    params.update(more_params)
                except (ValueError, json.decoder.JSONDecodeError) as error:
                    self.logger.debug(
                        'Unable to read "wsgi.input": {}'.format(error))
        else:
            params.update(parse_query_string(environ.get('QUERY_STRING')))
        return params

    def dispatch(self, environ, start_response):
        """
        Dispatches an HTTP request into a jsonrpc message, passes it to a
        handler, translates the results, and returns the HTTP response back
        to the requestor.

        :param environ: WSGI environment dictionary.
        :type environ: dict
        :param start_response: WSGI start_response callable.
        :type start_response: callable
        :returns: The body of the HTTP response.
        :rtype: Mixed
        """
        # Fail early if _bus has never been set.
        if self._bus is None:
            raise DispatcherError(
                'Bus can not be None when dispatching. '
                'Please call dispatcher.setup_bus().')

        # Add the routematch results to the WSGI environment dictionary.
        match_result = self._router.routematch(environ['PATH_INFO'], environ)
        if match_result is None:
            start_response(
                '404 Not Found',
                [('content-type', 'text/html')])
            return [bytes('Not Found', 'utf8')]
        environ['commissaire.routematch'] = match_result

        # Split up the route from the route data
        route, route_data = match_result

        # Get the parameters
        try:
            params = self._get_params(environ, route, route_data)
        except Exception as error:
            start_response(
                '400 Bad Request',
                [('content-type', 'text/html')])
            return [bytes('Bad Request', 'utf8')]

        # method is normally supposed to be the method to be called
        # but we hijack it for the method that was used over HTTP
        jsonrpc_msg = {
            'jsonrpc': '2.0',
            'id': str(uuid.uuid4()),
            'method': environ['REQUEST_METHOD'],
            'params': params,
        }

        self.logger.debug(
            'Request transformed to "{}".'.format(jsonrpc_msg))
        # Get the resulting message back
        try:
            # If the handler registered is a callable, use it
            if callable(route['controller']):
                handler = route['controller']
            # Else load what we found earlier
            else:
                handler = self._handler_map.get(route['controller'])
            self.logger.debug('Using controller {}->{}'.format(
                route, handler))

            result = handler(jsonrpc_msg, bus=self._bus)
            self.logger.debug(
                'Handler {} returned "{}"'.format(
                    route['controller'], result))
            if 'error' in result.keys():
                error = result['error']
                # If it's Invalid params handle it
                if error['code'] == JSONRPC_ERRORS['BAD_REQUEST']:
                    start_response(
                        '400 Bad Request',
                        [('content-type', 'application/json')])
                    return [bytes(json.dumps(error), 'utf8')]
                elif error['code'] == JSONRPC_ERRORS['NOT_FOUND']:
                    start_response(
                        '404 Not Found',
                        [('content-type', 'application/json')])
                    return [bytes(json.dumps(error), 'utf8')]
                elif error['code'] == JSONRPC_ERRORS['CONFLICT']:
                    start_response(
                        '409 Conflict',
                        [('content-type', 'application/json')])
                    return [bytes(json.dumps(error), 'utf8')]
                # Otherwise treat it like a 500 by raising
                raise Exception(result['error'])
            elif 'result' in result.keys():
                status = '200 OK'
                if environ['REQUEST_METHOD'] == 'PUT':
                    # action=add is for endpoints that add a
                    # member to a set, in which case nothing
                    # is being created, so return 200 OK.
                    if route.get('action') != 'add':
                        status = '201 Created'
                start_response(
                    status, [('content-type', 'application/json')])
                return [bytes(json.dumps(result['result']), 'utf8')]
        except Exception as error:
            self.logger.error(
                'Exception raised while {} handled "{}":\n{}'.format(
                    route['controller'], jsonrpc_msg,
                    traceback.format_exc()))
            start_response(
                '500 Internal Server Error',
                [('content-type', 'text/html')])
            return [bytes('Internal Server Error', 'utf8')]

        # Otherwise handle it as a generic 404
        start_response('404 Not Found', [('content-type', 'text/html')])
        return [bytes('Not Found', 'utf8')]
