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

from commissaire_http.handlers import create_response


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
