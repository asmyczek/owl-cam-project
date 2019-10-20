# -*- coding: utf-8 -*-
import cherrypy
from cherrypy.lib import auth_digest
from jinja2 import Environment, FileSystemLoader
from typing import Dict
from subprocess import check_output
import logging

from owlcam.utils import CONFIG, APP_LOG_HANDLER, GLOBAL_LOG_HANDLER, Switch, get_project_path, in_production
from owlcam.controller import Controller
from owlcam.__init__ import __version__


# Import pi module only if running on a Raspberry Pi,
# otherwise mock functions for development
if in_production():
    from owlcam.pi import cleanup_pi, pi_temperature
else:
    def cleanup_pi() -> None:
        logging.debug("Cleaning up PI config.")

    def pi_temperature() -> float:
        return 45.0


def get_ip_address() -> str:
    ip = check_output(["hostname", "-I"])
    return ip.decode("utf-8").strip()
        

class App(object):
    """Application routing class
    """

    def __init__(self) -> None:
        self.__env = Environment(loader=FileSystemLoader("webapp"))
        self.api: 'Api'

    @cherrypy.expose
    def index(self) -> str:
        template = self.__env.get_template("index.html")
        return template.render(version=__version__,
                               ip=get_ip_address())

    @cherrypy.expose
    def home(self) -> str:
        template = self.__env.get_template("home.html")
        return template.render(
            version=__version__,
            ip=get_ip_address(),
            temperature=int(pi_temperature()))

    @cherrypy.expose
    def logs(self) -> str:
        template = self.__env.get_template("logs.html")
        return template.render(version=__version__, 
                               logs=APP_LOG_HANDLER.get_logs())


@cherrypy.expose
class Api(object):
    """Api routing class
    """
    def __init__(self) -> None:
        self.toggle_light: 'ApiToggleSwitch'
        self.toggle_ir_light: 'ApiToggleSwitch'
        self.toggle_fan: 'ApiToggleSwitch'
        self.status: 'ApiStatus'


@cherrypy.expose
class ApiToggleSwitch(object):
    """Switch API router class for controlling switch states
    """

    def __init__(self, controller: Controller, switch: Switch):
        """
        :param controller: controller class
        :param switch: Switch to control, light, ir light or fan
        """
        self.__controller = controller
        self.__switch = switch

    @cherrypy.tools.json_out()
    def POST(self, **kwargs) -> Dict[str, bool]:
        return {'state': self.__controller.toggle_switch(self.__switch)}

@cherrypy.expose
class ApiStatus(object):
    """Application status API
    """

    def __init__(self, controller: Controller):
        self.__controller = controller

    @cherrypy.tools.json_out()
    def GET(self, **kwargs) -> Dict[str, object]:
        return {'switches':
                    {Switch.LIGHT.name.lower(): self.__controller.is_switch_on(Switch.LIGHT),
                     Switch.IR_LIGHT.name.lower(): self.__controller.is_switch_on(Switch.IR_LIGHT),
                     Switch.FAN.name.lower(): self.__controller.is_switch_on(Switch.FAN)}}


def start_server() -> None:
    """Web server initialization

    :return: None
    """

    controller = Controller()

    def stop_callback() -> None:
        controller.stop()
        cleanup_pi()

    app = App()
    app.api = Api()
    app.api.toggle_light = ApiToggleSwitch(controller, Switch.LIGHT)
    app.api.toggle_ir_light = ApiToggleSwitch(controller, Switch.IR_LIGHT)
    app.api.toggle_fan = ApiToggleSwitch(controller, Switch.FAN)
    app.api.status = ApiStatus(controller)

    users: Dict[str, str] = {CONFIG.server.user: CONFIG.server.password} #type: ignore

    auth_config = {
            'tools.auth_digest.on': True,
            'tools.auth_digest.realm': 'localhost',
            'tools.auth_digest.get_ha1': auth_digest.get_ha1_dict_plain(users),
            'tools.auth_digest.key': 'afa51d97d0948067097fd69cfc10b4da',
            'tools.auth_digest.accept_charset': 'UTF-8',
        }

    api_config = {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
            'tools.response_headers.on': True,
            'tools.response_headers.headers': [('Content-Type', 'text/json')],
        }

    app_config = {
        '/': {
            'tools.sessions.on': True,
            'tools.staticdir.root': str(get_project_path().absolute())
        },
        '/static': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': './webapp'
        },
        '/home': auth_config,
        '/logs': auth_config,
        '/api': { **api_config, **auth_config }
    }

    logging.getLogger("cherrypy").propagate = False
    logging.getLogger("cherrypy.error").addHandler(GLOBAL_LOG_HANDLER)

    global_config = {
        'log.screen': False,
        'log.access_file': '',
        'log.error_file': '',
        'server.socket_host': '0.0.0.0',
        'server.socket_port': CONFIG.server.port #type: ignore
    }
    cherrypy.config.update(global_config)
    cherrypy.engine.subscribe('stop', stop_callback)
    cherrypy.quickstart(app, '/', app_config)

