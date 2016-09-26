#!/usr/bin/env python3
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
Commissaire HTTP based application server.
"""
import argparse
import logging

from commissaire_http.server.routes import DISPATCHER
from commissaire_http import CommissaireHttpServer, parse_args


# TODO: Make this configurable
for name in ('Dispatcher', 'Router', 'Bus', 'CommissaireHttpServer'):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(name)s(%(levelname)s): %(message)s'))
    logger.handlers.append(handler)
# --


def main():
    """
    Main entry point.
    """
    epilog = 'Example: commissaire -c conf/myconfig.json'
    parser = argparse.ArgumentParser(epilog=epilog)
    try:
        args = parse_args(parser)
    except Exception as error:  # pragma: no cover
        parser.error(error)
    try:
        server = CommissaireHttpServer(
            args.listen_interface,
            args.listen_port,
            DISPATCHER)

        server.setup_bus(
            args.bus_exchange,
            args.bus_uri,
            [{'name': 'simple', 'routing_key': 'simple.*'}])
        server.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover
        pass


if __name__ == '__main__':  # pragma: no cover
    main()
