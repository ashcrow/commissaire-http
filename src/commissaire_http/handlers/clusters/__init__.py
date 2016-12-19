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

from commissaire import constants as C
from commissaire import models
from commissaire import bus as _bus
from commissaire_http.constants import JSONRPC_ERRORS

from commissaire_http.handlers import LOGGER, create_response, return_error


def _register(router):
    """
    Sets up routing for clusters.

    :param router: Router instance to attach to.
    :type router: commissaire_http.router.Router
    :returns: The router.
    :rtype: commissaire_http.router.Router
    """
    from commissaire_http.constants import ROUTING_RX_PARAMS

    router.connect(
        R'/api/v0/clusters/',
        controller=list_clusters,
        conditions={'method': 'GET'})
    router.connect(
        R'/api/v0/cluster/{name}/',
        requirements={'name': ROUTING_RX_PARAMS['name']},
        controller=get_cluster,
        conditions={'method': 'GET'})
    router.connect(
        R'/api/v0/cluster/{name}/',
        requirements={'name': ROUTING_RX_PARAMS['name']},
        controller=create_cluster,
        conditions={'method': 'PUT'})
    router.connect(
        R'/api/v0/cluster/{name}/',
        requirements={'name': ROUTING_RX_PARAMS['name']},
        controller=delete_cluster,
        conditions={'method': 'DELETE'})
    router.connect(
        R'/api/v0/cluster/{name}/hosts/',
        requirements={'name': ROUTING_RX_PARAMS['name']},
        controller=list_cluster_members,
        conditions={'method': 'GET'})
    router.connect(
        R'/api/v0/cluster/{name}/hosts/',
        requirements={'name': ROUTING_RX_PARAMS['name']},
        controller=update_cluster_members,
        conditions={'method': 'PUT'},
        action='add')
    router.connect(
        R'/api/v0/cluster/{name}/hosts/{host}/',
        requirements={
            'name': ROUTING_RX_PARAMS['name'],
            'host': ROUTING_RX_PARAMS['host'],
        },
        controller=check_cluster_member,
        conditions={'method': 'GET'})
    router.connect(
        R'/api/v0/cluster/{name}/hosts/{host}/',
        requirements={
            'name': ROUTING_RX_PARAMS['name'],
            'host': ROUTING_RX_PARAMS['host'],
        },
        controller=add_cluster_member,
        conditions={'method': 'PUT'},
        action='add')
    router.connect(
        R'/api/v0/cluster/{name}/hosts/{host}/',
        requirements={
            'name': ROUTING_RX_PARAMS['name'],
            'host': ROUTING_RX_PARAMS['host'],
        },
        controller=delete_cluster_member,
        conditions={'method': 'DELETE'})

    return router


def list_clusters(message, bus):
    """
    Lists all clusters.

    :param message: jsonrpc message structure.
    :type message: dict
    :param bus: Bus instance.
    :type bus: commissaire_http.bus.Bus
    :returns: A jsonrpc structure.
    :rtype: dict
    """
    container = bus.storage.list(models.Clusters)
    return create_response(
        message['id'],
        [cluster.name for cluster in container.clusters])


def get_cluster(message, bus):
    """
    Gets a specific cluster.

    :param message: jsonrpc message structure.
    :type message: dict
    :param bus: Bus instance.
    :type bus: commissaire_http.bus.Bus
    :returns: A jsonrpc structure.
    :rtype: dict
    """
    name = message['params']['name']
    cluster = bus.storage.get_cluster(name)

    available = unavailable = total = 0

    cluster.status = C.CLUSTER_STATUS_OK
    for host_address in cluster.hostset:
        host = bus.storage.get(host_address)
        total += 1
        if host.status == 'active':
            available += 1
        else:
            unavailable += 1
            cluster.status = C.CLUSTER_STATUS_DEGRADED

    # If we have 1 or more hosts and none are active consider the cluster
    # in failed status
    if total > 0 and total == unavailable:
        cluster.status = C.CLUSTER_STATUS_FAILED
    cluster.hosts['total'] = total
    cluster.hosts['available'] = available
    cluster.hosts['unavailable'] = unavailable

    return create_response(message['id'], cluster.to_dict_with_hosts())


def create_cluster(message, bus):
    """
    Creates a new cluster.

    :param message: jsonrpc message structure.
    :type message: dict
    :param bus: Bus instance.
    :type bus: commissaire_http.bus.Bus
    :returns: A jsonrpc structure.
    :rtype: dict
    """
    try:
        name = message['params']['name']
        bus.storage.get_cluster(name)
        LOGGER.debug(
            'Creation of already exisiting cluster {0} requested.'.format(
                name))
    except Exception as error:
        LOGGER.debug('Brand new cluster being created.')

        network_name = message['params'].get('network')
        if network_name:
            # Verify the networks existence
            try:
                bus.storage.get_network(network_name)
            except Exception as error:
                # Default if the network doesn't exist
                message['params']['network'] = C.DEFAULT_CLUSTER_NETWORK_JSON['name']  # noqa

    try:
        cluster = bus.storage.save(models.Cluster.new(**message['params']))
        return create_response(message['id'], cluster.to_dict_safe())
    except models.ValidationError as error:
        return return_error(message, error, JSONRPC_ERRORS['INVALID_REQUEST'])


def delete_cluster(message, bus):
    """
    Deletes an existing cluster.

    :param message: jsonrpc message structure.
    :type message: dict
    :param bus: Bus instance.
    :type bus: commissaire_http.bus.Bus
    :returns: A jsonrpc structure.
    :rtype: dict
    """
    try:
        name = message['params']['name']
        LOGGER.debug('Attempting to delete cluster "{}"'.format(name))
        bus.storage.delete(models.Cluster.new(name=name))
        return create_response(message['id'], [])
    except _bus.RemoteProcedureCallError as error:
        return return_error(message, error, JSONRPC_ERRORS['NOT_FOUND'])
    except Exception as error:
        LOGGER.debug('Error deleting cluster: {}: {}'.format(
            type(error), error))
        return return_error(message, error, JSONRPC_ERRORS['INTERNAL_ERROR'])


def list_cluster_members(message, bus):
    """
    Lists hosts in a cluster.

    :param message: jsonrpc message structure.
    :type message: dict
    :param bus: Bus instance.
    :type bus: commissaire_http.bus.Bus
    :returns: A jsonrpc structure.
    :rtype: dict
    """
    try:
        name = message['params']['name']
        cluster = bus.storage.get_cluster(name)
        LOGGER.debug('Cluster found: {}'.format(cluster.name))
        LOGGER.debug('Returning: {}'.format(cluster.hostset))
        return create_response(
            message['id'], result=cluster.hostset)
    except Exception as error:
        return return_error(message, error, JSONRPC_ERRORS['NOT_FOUND'])


def update_cluster_members(message, bus):
    """
    Updates the list of members in a cluster.

    :param message: jsonrpc message structure.
    :type message: dict
    :param bus: Bus instance.
    :type bus: commissaire_http.bus.Bus
    :returns: A jsonrpc structure.
    :rtype: dict
    """
    try:
        old_hosts = set(message['params']['old'])  # Ensures no duplicates
        new_hosts = set(message['params']['new'])  # Ensures no duplicates
        LOGGER.debug('old_hosts="{}", new_hosts="{}"'.format(
            old_hosts, new_hosts))
    except Exception as error:
        return return_error(message, error, JSONRPC_ERRORS['BAD_REQUEST'])

    try:
        name = message['params']['name']
        cluster = bus.storage.get_cluster(name)
    except Exception as error:
        return return_error(message, error, JSONRPC_ERRORS['NOT_FOUND'])

    if old_hosts != set(cluster.hostset):
        msg = 'Conflict setting hosts for cluster {0}'.format(name)
        LOGGER.error(msg)
        return return_error(message, msg, JSONRPC_ERRORS['CONFLICT'])

    # FIXME: Need input validation.  For each new host,
    #        - Does the host exist at /commissaire/hosts/{IP}?
    #        - Does the host already belong to another cluster?

    # FIXME: Should guard against races here, since we're fetching
    #        the cluster record and writing it back with some parts
    #        unmodified.  Use either locking or a conditional write
    #        with the etcd 'modifiedIndex'.  Deferring for now.
    cluster.hostset = list(new_hosts)
    saved_cluster = bus.storage.save(cluster)
    # XXX Using to_dict() instead of to_dict_safe() to include hostset.
    return create_response(message['id'], saved_cluster.to_dict())


def check_cluster_member(message, bus):
    """
    Checks is a member is part of the cluster.

    :param message: jsonrpc message structure.
    :type message: dict
    :param bus: Bus instance.
    :type bus: commissaire_http.bus.Bus
    :returns: A jsonrpc structure.
    :rtype: dict
    """
    try:
        host = message['params']['host']
        name = message['params']['name']
        cluster = bus.storage.get_cluster(name)
        if host in cluster.hostset:
            # Return back the host in a list
            return create_response(message['id'], [host])
        else:
            return create_response(
                message['id'],
                error='The requested host is not part of the cluster.',
                error_code=JSONRPC_ERRORS['NOT_FOUND'])
    except Exception as error:
        return create_response(
            message['id'],
            error=error,
            error_code=JSONRPC_ERRORS['INTERNAL_ERROR'])


def add_cluster_member(message, bus):
    """
    Adds a member to the cluster.

    :param message: jsonrpc message structure.
    :type message: dict
    :param bus: Bus instance.
    :type bus: commissaire_http.bus.Bus
    :returns: A jsonrpc structure.
    :rtype: dict
    """
    try:
        host = message['params']['host']
        name = message['params']['name']
        cluster = bus.storage.get_cluster(name)

        if host not in cluster.hostset:
            # FIXME: Need input validation.
            #        - Does the host exist at /commissaire/hosts/{IP}?
            #        - Does the host already belong to another cluster?

            # FIXME: Should guard against races here, since we're fetching
            #        the cluster record and writing it back with some parts
            #        unmodified.  Use either locking or a conditional write
            #        with the etcd 'modifiedIndex'.  Deferring for now.
            cluster.hostset.append(host)
            bus.storage.save(cluster)

        # Return back the host in a list
        return create_response(message['id'], [host])
    except Exception as error:
        return create_response(
            message['id'],
            error=error,
            error_code=JSONRPC_ERRORS['INTERNAL_ERROR'])


def delete_cluster_member(message, bus):
    """
    Deletes a member from the cluster.

    :param message: jsonrpc message structure.
    :type message: dict
    :param bus: Bus instance.
    :type bus: commissaire_http.bus.Bus
    :returns: A jsonrpc structure.
    :rtype: dict
    """
    try:
        host = message['params']['host']
        name = message['params']['name']
        cluster = bus.storage.get_cluster(name)
        if host in cluster.hostset:
            # FIXME: Should guard against races here, since we're fetching
            #        the cluster record and writing it back with some parts
            #        unmodified.  Use either locking or a conditional write
            #        with the etcd 'modifiedIndex'.  Deferring for now.
            idx = cluster.hostset.index(host)
            cluster.hostset.pop(idx)
            bus.storage.save(cluster)
        return create_response(message['id'], [])
    except Exception as error:
        return create_response(
            message['id'],
            error=error,
            error_code=JSONRPC_ERRORS['NOT_FOUND'])