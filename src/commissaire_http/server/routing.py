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
Routing items.
"""

from commissaire_http.dispatcher import Dispatcher
from commissaire_http.router import Router

#: Global HTTP router for the dispatcher
ROUTER = Router()
ROUTER.connect(
    R'/api/v0/clusters/',
    controller='commissaire_http.handlers.clusters.list_clusters',
    conditions={'method': 'GET'})
ROUTER.connect(
    R'/api/v0/cluster/{name}/',
    requirements={'name': R'[a-zA-Z0-9\-\_]+'},
    controller='commissaire_http.handlers.clusters.get_cluster',
    conditions={'method': 'GET'})


#: Global HTTP dispatcher for the server
DISPATCHER = Dispatcher(
    ROUTER,
    handler_packages=[
        'commissaire_http.handlers',
        'commissaire_http.handlers.clusters'])
