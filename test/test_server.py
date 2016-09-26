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
Test for commissaire_http.server
"""

from unittest import mock

from . import TestCase

from commissaire_http.server.cli import main


class TestServerCli(TestCase):
    """
    Test for the server cli module.
    """

    @mock.patch('commissaire_http.server.cli.CommissaireHttpServer')
    def test_main(self, _server):
        """
        Verify the server is started when main is executed.
        """
        main()
        _server().serve_forever.assert_called_once_with()
