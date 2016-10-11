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
Networks handlers.
"""

from commissaire import bus as _bus
from commissaire_http.constants import JSONRPC_ERRORS
from commissaire_http.handlers import LOGGER, create_response, return_error


def list_hosts(message, bus):
    """
    Lists all hosts.

    :param message: jsonrpc message structure.
    :type message: dict
    :param bus: Bus instance.
    :type bus: commissaire_http.bus.Bus
    :returns: A jsonrpc structure.
    :rtype: dict
    """
    hosts_msg = bus.request('storage.list', params=['Hosts'])
    return create_response(message['id'], hosts_msg['result'])


def get_host(message, bus):
    """
    Gets a specific host.

    :param message: jsonrpc message structure.
    :type message: dict
    :param bus: Bus instance.
    :type bus: commissaire_http.bus.Bus
    :returns: A jsonrpc structure.
    :rtype: dict
    """
    try:
        host_response = bus.request(
            'storage.get', params=[
                'Host', {'address': message['params']['address']}])
        return create_response(message['id'], host_response['result'])
    except _bus.RemoteProcedureCallError as error:
        LOGGER.debug('Client requested a non-existant host: "{}"'.format(
            message['params']['address']))
        return return_error(message, error, JSONRPC_ERRORS['NOT_FOUND'])


def delete_host(message, bus):
    """
    Deletes an exisiting host.

    :param message: jsonrpc message structure.
    :type message: dict
    :param bus: Bus instance.
    :type bus: commissaire_http.bus.Bus
    :returns: A jsonrpc structure.
    :rtype: dict
    """
    # TODO: kick off service job to remove the host
    try:
        LOGGER.debug('Attempting to delete host "{}"'.format(
            message['params']['address']))
        bus.request('storage.delete', params=[
            'Host', {'address': message['params']['address']}])
        return create_response(message['id'], [])
    except _bus.RemoteProcedureCallError as error:
        LOGGER.debug('Error deleting host: {}: {}'.format(
            type(error), error))
        return return_error(message, error, JSONRPC_ERRORS['NOT_FOUND'])
    except Exception as error:
        LOGGER.debug('Error deleting host: {}: {}'.format(
            type(error), error))
        return return_error(message, error, JSONRPC_ERRORS['INTERNAL_ERROR'])


def get_hostcreds(message, bus):
    """
    Gets credentials for a host.

    :param message: jsonrpc message structure.
    :type message: dict
    :param bus: Bus instance.
    :type bus: commissaire_http.bus.Bus
    :returns: A jsonrpc structure.
    :rtype: dict
    """
    try:
        host_response = bus.request(
            'storage.get', params=[
                'Host', {'address': message['params']['address']}, True])
        creds = {
            'remote_user': host_response['result']['remote_user'],
            'ssh_priv_key': host_response['result']['ssh_priv_key']
        }
        return create_response(message['id'], creds)
    except _bus.RemoteProcedureCallError as error:
        LOGGER.debug('Client requested a non-existant host: "{}"'.format(
            message['params']['address']))
        return return_error(message, error, JSONRPC_ERRORS['NOT_FOUND'])
