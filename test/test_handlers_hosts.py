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
Test for commissaire_http.handlers.hosts module.
"""

from unittest import mock

from . import TestCase

from commissaire import bus as _bus
from commissaire.constants import JSONRPC_ERRORS
from commissaire_http.handlers import hosts, create_response, clusters
from commissaire.models import Host, ValidationError

# Globals reused in network tests
#: Message ID
ID = '123'
#: Generic host instance
HOST = Host.new(address='127.0.0.1')
#: Generic jsonrpc network request by address
SIMPLE_HOST_REQUEST = {
    'jsonrpc': '2.0',
    'id': ID,
    'params': {'address': 'test'},
}


class Test_hosts(TestCase):
    """
    Test for the Hosts handlers.
    """

    def test_list_hosts(self):
        """
        Verify list_hosts responds with the right information.
        """
        bus = mock.MagicMock()
        bus.request.return_value = {
            'jsonrpc': '2.0',
            'result': [HOST.to_dict()],
            'id': '123'}
        self.assertEquals(
            create_response(ID, [HOST.to_dict()]),
            hosts.list_hosts(SIMPLE_HOST_REQUEST, bus))

    def test_get_host(self):
        """
        Verify get_host responds with the right information.
        """
        bus = mock.MagicMock()
        bus.request.return_value = create_response(ID, HOST.to_dict())
        self.assertEquals(
            create_response(ID, HOST.to_dict()),
            hosts.get_host(SIMPLE_HOST_REQUEST, bus))

    def test_get_host_that_doesnt_exist(self):
        """
        Verify get_host responds with a 404 error on missing hosts.
        """
        bus = mock.MagicMock()
        bus.request.side_effect = _bus.RemoteProcedureCallError('test')

        expected = create_response(
            ID, error='error',
            error_code=JSONRPC_ERRORS['NOT_FOUND'])
        expected['error']['message'] = mock.ANY
        expected['error']['data'] = mock.ANY

        self.assertEquals(
            expected,
            hosts.get_host(SIMPLE_HOST_REQUEST, bus))
