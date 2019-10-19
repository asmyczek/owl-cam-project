# -*- coding: utf-8 -*-

from owlcam.server import start_server
import logging


def main():
    """
    Start Web Server
    """
    logging.info('Initialising owl cam server')
    try:

        start_server()

    finally:
        logging.info('Owl cam server stopped')


if __name__ == '__main__':
    main()