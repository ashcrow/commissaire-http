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
Test for commissaire_http.handlers.clusters.operations module.
"""
import copy

from unittest import mock

from . import TestCase, expected_error

from commissaire import bus as _bus
from commissaire import constants as C
from commissaire.constants import JSONRPC_ERRORS
from commissaire_http.handlers.clusters import (
    operations, create_response, return_error)
from commissaire.models import ClusterDeploy

# Globals reused in host tests
#: Message ID
ID = '123'
#: Generic host instance
CLUSTER_DEPLOY = ClusterDeploy.new(name='test', version='123')
#: Generic jsonrpc host request by address
SIMPLE_DEPLOY_REQUEST = {
    'jsonrpc': '2.0',
    'id': ID,
    'params': CLUSTER_DEPLOY.to_dict(),
}
#: Bad version for testing
BAD_CLUSTER_DEPLOY = ClusterDeploy.new(name='bad', version=None)
#: Bad request for testing
BAD_DEPLOY_REQUEST = {
    'jsonrpc': '2.0',
    'id': ID,
    'params': BAD_CLUSTER_DEPLOY.to_dict(),
}


class Test_deploy_operations(TestCase):
    """
    Test for the ClusterDeploy operation handlers.
    """

    def test_get_cluster_deploy(self):
        """
        Verify get_cluster_deploy responds with the right information.
        """
        bus = mock.MagicMock()
        bus.request.return_value = create_response(
            ID, CLUSTER_DEPLOY.to_dict())
        self.assertEquals(
            create_response(ID, CLUSTER_DEPLOY.to_dict()),
            operations.get_cluster_deploy(SIMPLE_DEPLOY_REQUEST, bus))

    def test_get_cluster_deploy_that_doesnt_exist(self):
        """
        Verify get_cluster_deploy responds with a 404 error on missing cluster.
        """
        bus = mock.MagicMock()
        bus.request.side_effect = _bus.RemoteProcedureCallError('test')

        self.assertEquals(
            expected_error(ID, JSONRPC_ERRORS['NOT_FOUND']),
            operations.get_cluster_deploy(SIMPLE_DEPLOY_REQUEST, bus))

    def test_get_cluster_deploy_with_invalid_data(self):
        """
        Verify get_cluster_deploy responds with an error when invalid data is given.
        """
        bus = mock.MagicMock()
        bus.request.return_value = create_response(
            ID, BAD_CLUSTER_DEPLOY.to_dict())

        self.assertEquals(
            expected_error(ID, JSONRPC_ERRORS['INVALID_PARAMETERS']),
            operations.get_cluster_deploy(
                BAD_DEPLOY_REQUEST, bus))

    def test_create_cluster_deploy(self):
        """
        Verify create_cluster_deploy creates a new deploy record.
        """
        bus = mock.MagicMock()
        bus.request.return_value = create_response(
            ID, CLUSTER_DEPLOY.to_dict())

        self.assertEquals(
            create_response(ID, CLUSTER_DEPLOY.to_dict()),
            operations.create_cluster_deploy(
                SIMPLE_DEPLOY_REQUEST, bus))

    def test_create_cluster_deploy_with_invalid_data(self):
        """
        Verify create_cluster_deploy responds with an error when invalid data is given.
        """
        bus = mock.MagicMock()
        bus.request.return_value = create_response(
            ID, BAD_CLUSTER_DEPLOY.to_dict())

        self.assertEquals(
            expected_error(ID, JSONRPC_ERRORS['INVALID_PARAMETERS']),
            operations.create_cluster_deploy(
                BAD_DEPLOY_REQUEST, bus))

    def test_create_cluster_deploy_with_rpc_error(self):
        """
        Verify create_cluster_deploy responds with an error when an rpc error occurs.
        """
        bus = mock.MagicMock()
        bus.request.side_effect = _bus.RemoteProcedureCallError('test')

        self.assertEquals(
            expected_error(ID, JSONRPC_ERRORS['INTERNAL_ERROR']),
            operations.create_cluster_deploy(
                SIMPLE_DEPLOY_REQUEST, bus))
