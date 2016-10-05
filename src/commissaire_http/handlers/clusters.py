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
from commissaire_http.constants import JSONRPC_ERRORS
from commissaire import models

from commissaire_http.handlers import LOGGER, create_response, return_error


def list_clusters(message, bus):
    """
    Lists all clusters.

    :param message: jsonrpc message structure.
    :type message: dict
    :returns: A jsonrpc structure.
    :rtype: dict
    """
    clusters_msg = bus.request('storage.list', 'list', params=['Clusters'])
    return create_response(
        message['id'],
        [cluster['name'] for cluster in clusters_msg['result']])


def get_cluster(message, bus):
    """
    Lists all clusters.

    :param message: jsonrpc message structure.
    :type message: dict
    :returns: A jsonrpc structure.
    :rtype: dict
    """
    cluster = bus.request(
        'storage.get', 'get', params=[
            'Cluster', {'name': message['params']['name']}])
    return create_response(message['id'], cluster['result'])


def create_cluster(message, bus):
    """
    Creates a new cluster.

    :param message: jsonrpc message structure.
    :type message: dict
    :returns: A jsonrpc structure.
    :rtype: dict
    """
    try:
        bus.request('storage.get', 'get', params=[
            'Cluster', {'name': message['params']['name']}])
        LOGGER.debug(
            'Creation of already exisiting cluster {0} requested.'.format(
                message['params']['name']))
    except Exception as error:
        LOGGER.debug('Brand new cluster being created.')

        if message['params'].get('network'):
            # Verify the networks existence
            try:
                bus.request('storage.get', 'get', params=[
                    'Network', {'name': message['params']['network']}
                ])
            except Exception as error:
                # Default if the network doesn't exist
                message['params']['network'] = C.DEFAULT_CLUSTER_NETWORK_JSON['name']  # noqa

    try:
        cluster = models.Cluster.new(**message['params'])
        cluster._validate()
        response = bus.request(
            'storage.save', 'save', params=[
                'Cluster', cluster.to_dict()])
        return create_response(message['id'], response['result'])
    except models.ValidationError as error:
        return return_error(message, error, JSONRPC_ERRORS['INVALID_REQUEST'])


def list_cluster_members(message, bus):
    """
    Lists hosts in a cluster.

    :param message: jsonrpc message structure.
    :type message: dict
    :returns: A jsonrpc structure.
    :rtype: dict
    """
    response = None
    try:
        cluster = bus.request('storage.get', 'get', params=[
            'Cluster', {'name': message['params']['name']}])
        LOGGER.debug('Cluster found: {}'.format(cluster['result']['name']))
        LOGGER.debug('Returning: {}'.format(response))
        return create_response(
            message['id'], result=cluster['result']['hostset'])
    except Exception as error:
        return return_error(message, error, JSONRPC_ERRORS['NOT_FOUND'])


def update_cluster_memebers(message, bus):
    """
    Lists hosts in a cluster.

    :param message: jsonrpc message structure.
    :type message: dict
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
        cluster = bus.request('storage.get', 'get', params=[
            'Cluster', {'name': message['params']['name']}])
    except Exception as error:
        return return_error(message, error, JSONRPC_ERRORS['NOT_FOUND'])

    if old_hosts != set(cluster['result']['hostset']):
        msg = 'Conflict setting hosts for cluster {0}'.format(
            cluster['result']['name'])
        LOGGER.error(msg)
        # TODO 409
        return return_error(message, msg, JSONRPC_ERRORS['NOT_FOUND'])

    cluster['result']['hostset'] = list(new_hosts)
    cluster = models.Cluster.new(**cluster['result'])
    cluster._validate()
    response = bus.request(
        'storage.save', 'save', params=[
            'Cluster', cluster.to_dict()])
    return create_response(message['id'], response['result'])
