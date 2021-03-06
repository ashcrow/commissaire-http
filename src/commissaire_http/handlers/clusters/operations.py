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
Clusters handlers.
"""

import datetime

from commissaire import models
from commissaire import bus as _bus
from commissaire_http.constants import JSONRPC_ERRORS

from commissaire_http.handlers import (
    LOGGER, JSONRPC_Handler, create_jsonrpc_response, create_jsonrpc_error)


def _register(router):
    """
    Sets up routing for cluster operations.

    :param router: Router instance to attach to.
    :type router: commissaire_http.router.Router
    :returns: The router.
    :rtype: commissaire_http.router.Router
    """
    from commissaire_http.constants import ROUTING_RX_PARAMS

    router.connect(
        R'/api/v0/cluster/{name}/deploy',
        requirements={'name': ROUTING_RX_PARAMS['name']},
        controller=get_cluster_deploy,
        conditions={'method': 'GET'})
    router.connect(
        R'/api/v0/cluster/{name}/deploy',
        requirements={'name': ROUTING_RX_PARAMS['name']},
        controller=create_cluster_deploy,
        conditions={'method': 'PUT'})
    # Upgrade
    router.connect(
        R'/api/v0/cluster/{name}/upgrade',
        requirements={'name': ROUTING_RX_PARAMS['name']},
        controller=get_cluster_upgrade,
        conditions={'method': 'GET'})
    router.connect(
        R'/api/v0/cluster/{name}/upgrade',
        requirements={'name': ROUTING_RX_PARAMS['name']},
        controller=create_cluster_upgrade,
        conditions={'method': 'PUT'})
    # Restart
    router.connect(
        R'/api/v0/cluster/{name}/restart',
        requirements={'name': ROUTING_RX_PARAMS['name']},
        controller=get_cluster_restart,
        conditions={'method': 'GET'})
    router.connect(
        R'/api/v0/cluster/{name}/restart',
        requirements={'name': ROUTING_RX_PARAMS['name']},
        controller=create_cluster_restart,
        conditions={'method': 'PUT'})

    return router


@JSONRPC_Handler
def get_cluster_deploy(message, bus):
    """
    Gets a specific deployment.

    :param message: jsonrpc message structure.
    :type message: dict
    :param bus: Bus instance.
    :type bus: commissaire_http.bus.Bus
    :returns: A jsonrpc structure.
    :rtype: dict
    """
    try:
        name = message['params']['name']
        cluster_deploy = bus.storage.get(models.ClusterDeploy.new(name=name))
        cluster_deploy._validate()

        return create_jsonrpc_response(
            message['id'], cluster_deploy.to_dict_safe())
    except models.ValidationError as error:
        LOGGER.info('Invalid data retrieved. "{}"'.format(error))
        LOGGER.debug('Data="{}"'.format(message['params']))
        return create_jsonrpc_error(
            message, error, JSONRPC_ERRORS['INVALID_REQUEST'])
    except _bus.StorageLookupError as error:
        return create_jsonrpc_error(
            message, error, JSONRPC_ERRORS['NOT_FOUND'])
    except Exception as error:
        return create_jsonrpc_error(
            message, error, JSONRPC_ERRORS['INTERNAL_ERROR'])


@JSONRPC_Handler
def create_cluster_deploy(message, bus):
    """
    Creates a new cluster deployment.

    :param message: jsonrpc message structure.
    :type message: dict
    :param bus: Bus instance.
    :type bus: commissaire_http.bus.Bus
    :returns: A jsonrpc structure.
    :rtype: dict
    """
    try:
        cluster_deploy = models.ClusterDeploy.new(
            name=message['params'].get('name'),
            version=message['params'].get('version'))
        cluster_deploy._validate()

        result = bus.request(
            'jobs.clusterexec.deploy', params=[
                cluster_deploy.name,
                cluster_deploy.version])
        return create_jsonrpc_response(message['id'], result['result'])
    except models.ValidationError as error:
        LOGGER.info('Invalid data provided. "{}"'.format(error))
        LOGGER.debug('Data="{}"'.format(message['params']))
        return create_jsonrpc_error(
            message, error, JSONRPC_ERRORS['INVALID_REQUEST'])
    except Exception as error:
        LOGGER.debug('Error creating ClusterDeploy: {}: {}'.format(
            type(error), error))
        return create_jsonrpc_error(
            message, error, JSONRPC_ERRORS['INTERNAL_ERROR'])


@JSONRPC_Handler
def get_cluster_upgrade(message, bus):  # pragma: no cover
    """
    Gets a new cluster upgrade.

    :param message: jsonrpc message structure.
    :type message: dict
    :param bus: Bus instance.
    :type bus: commissaire_http.bus.Bus
    :returns: A jsonrpc structure.
    :rtype: dict
    """
    return get_cluster_operation(models.ClusterUpgrade, message, bus)


@JSONRPC_Handler
def create_cluster_upgrade(message, bus):  # pragma: no cover
    """
    Creates a new cluster upgrade.

    :param message: jsonrpc message structure.
    :type message: dict
    :param bus: Bus instance.
    :type bus: commissaire_http.bus.Bus
    :returns: A jsonrpc structure.
    :rtype: dict
    """
    return create_cluster_operation(
        models.ClusterUpgrade, message, bus, 'jobs.clusterexec.upgrade')


@JSONRPC_Handler
def get_cluster_restart(message, bus):  # pragma: no cover
    """
    Gets a new cluster restart.

    :param message: jsonrpc message structure.
    :type message: dict
    :param bus: Bus instance.
    :type bus: commissaire_http.bus.Bus
    :returns: A jsonrpc structure.
    :rtype: dict
    """
    return get_cluster_operation(models.ClusterRestart, message, bus)


@JSONRPC_Handler
def create_cluster_restart(message, bus):  # pragma: no cover
    """
    Creates a new cluster restart.

    :param message: jsonrpc message structure.
    :type message: dict
    :param bus: Bus instance.
    :type bus: commissaire_http.bus.Bus
    :returns: A jsonrpc structure.
    :rtype: dict
    """
    return create_cluster_operation(
        models.ClusterRestart, message, bus, 'jobs.clusterexec.restart')


def get_cluster_operation(model_cls, message, bus):
    """
    Gets a specific operation based on the model_cls.

    :param model_cls: The model class to use.
    :type model_cls: class
    :param message: jsonrpc message structure.
    :type message: dict
    :param bus: Bus instance.
    :type bus: commissaire_http.bus.Bus
    :returns: A jsonrpc structure.
    :rtype: dict
    """
    try:
        name = message['params']['name']
        model = bus.storage.get(model_cls.new(name=name))
        model._validate()

        return create_jsonrpc_response(message['id'], model.to_dict_safe())
    except models.ValidationError as error:
        LOGGER.info('Invalid data retrieved. "{}"'.format(error))
        LOGGER.debug('Data="{}"'.format(message['params']))
        return create_jsonrpc_error(
            message, error, JSONRPC_ERRORS['INVALID_REQUEST'])
    except _bus.StorageLookupError as error:
        return create_jsonrpc_error(
            message, error, JSONRPC_ERRORS['NOT_FOUND'])
    except Exception as error:
        LOGGER.debug('Error getting {}: {}: {}'.format(
            model_cls.__name__, type(error), error))
        return create_jsonrpc_error(
            message, error, JSONRPC_ERRORS['INTERNAL_ERROR'])


def create_cluster_operation(model_cls, message, bus, routing_key):
    """
    Creates a new operation based on the model_cls.

    :param model_cls: The model class to use.
    :type model_cls: class
    :param message: jsonrpc message structure.
    :type message: dict
    :param bus: Bus instance.
    :type bus: commissaire_http.bus.Bus
    :returns: A jsonrpc structure.
    :param routing_key: Routing key for the cluster operation request.
    :type routing_key: str
    :rtype: dict
    """

    # Verify cluster exists first
    cluster_name = message['params']['name']
    try:
        bus.storage.get_cluster(cluster_name)
        LOGGER.debug('Found cluster "{}"'.format(cluster_name))
    except:
        error_msg = 'Cluster "{}" does not exist.'.format(cluster_name)
        LOGGER.debug(error_msg)
        return create_jsonrpc_error(
            message, error_msg, JSONRPC_ERRORS['NOT_FOUND'])

    try:
        model = model_cls.new(
            name=cluster_name,
            started_at=datetime.datetime.utcnow().isoformat())
        model._validate()

        # XXX Assumes the only method argument is cluster_name.
        result = bus.request(routing_key, params=[cluster_name])
        return create_jsonrpc_response(message['id'], result['result'])
    except models.ValidationError as error:
        LOGGER.info('Invalid data provided. "{}"'.format(error))
        LOGGER.debug('Data="{}"'.format(message['params']))
        return create_jsonrpc_error(
            message, error, JSONRPC_ERRORS['INVALID_REQUEST'])
    except Exception as error:
        LOGGER.debug('Error creating {}: {}: {}'.format(
            model_cls.__name__, type(error), error))
        return create_jsonrpc_error(
            message, error, JSONRPC_ERRORS['INTERNAL_ERROR'])
