import argparse
import textwrap
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from typing import Dict,  Type, Tuple, Optional

from expkit.base.architecture import Platform, Architecture
from expkit.base.command.base import CommandTemplate, CommandOptions
from expkit.base.logger import get_logger
from expkit.framework.database import register_command
from ipaddress import ip_address, IPv4Address, IPv6Address


LOGGER = get_logger(__name__)


class ServerOptions(CommandOptions):
    def __init__(self):
        super().__init__()
        self.server_port: int = 8080
        self.num_artifacts_prepare: int = 0
        self.server_host: IPv4Address | IPv6Address = ip_address("0.0.0.0")
        self.request_handler: Optional["ServerBaseRequestHandler"] = None
        self.request_handler_data: dict = {}


class ServerBaseRequestHandler:
    def __init__(self):
        self.server_cmd: Optional["ServerCommand"] = None
        self.options: Optional[ServerOptions] = None

    def extend_argparse(self, parser: argparse.ArgumentParser):
        pass

    def parse_arguments(self, args: argparse.Namespace, options: ServerOptions):
        pass

    def handle_request(self, handler: BaseHTTPRequestHandler, method: str):
        handler.send_response(404)
        handler.end_headers()

    def initialize(self, server: "ServerCommand", options: ServerOptions):
        self.server_cmd = server
        self.options = options


REQUEST_HANDLERS: Dict[str, Type[ServerBaseRequestHandler]] = {}


def register_server_request_parser(*args, **kwargs):
    def decorator(func):
        name = args[0]

        if name in REQUEST_HANDLERS:
            raise ValueError(f"Server request handler {name} already registered")

        REQUEST_HANDLERS[name] = func
        return func

    if len(args) == 1 and len(kwargs) == 0 and not isinstance(args[0], str):
        raise ValueError("Decorator must be called with request handler name as parameter")
    if len(args) > 1:
        raise ValueError("Decorator must be called with request handler name as parameter")
    if len(kwargs) > 0:
        raise ValueError("Decorator must be called with request handler name as parameter")
    assert len(args) == 1 and len(kwargs) == 0 and callable(args[0]) is False, "Decorator must be called with request handler name as parameter"
    if len(args) == 1 and not isinstance(args[0], str):
        raise ValueError("Decorator must be called with request handler name as parameter")

    return decorator


@register_command
class ServerCommand(CommandTemplate):
    __instance = None

    def __init__(self):
        super().__init__(".server", textwrap.dedent('''\
            Builds and serves an exploit on the fly when a client connects to the local server.
            '''), textwrap.dedent('''\
            Starts a webserver to build the exploit configuration defined in
            the config.json file on the fly whenever a request is received.
            Within the request the information about the target system like
            os and architecture must be contained. The server will then
            build the specific exploit for this configuration and returns it
            to the client.
            To prevent signature detection the server can be configured using
            the request handler argument how to infer the above specified information
            from the web request. The default request handler is the simple_get
            handler which expects the information to be contained in the url path.
            The request must be a GET request with the following parameters:
            1. os: The target platform (WINDOWS, LINUX, MACOS, ...).
            2. arch: The target architecture (i386, AMD64, ARM, ARM64, ...).
            3. target: The target artifact to build from the config.json file.
            4. token: The token to authenticate the request (can be specified as parameter).
            If no token is set, the server will accept all requests.
            The response will the payload. If the payload is
            platform independent, the platform and arch parameters should be
            set to "DUMMY". An error will be signaled by returning no data or status != 200.
            The server will listen on port 8080 and is bound to ip 0.0.0.0 by default.
            '''), options=ServerOptions)

        self.__lock = threading.Lock()
        self.__request_lock = threading.Lock()

        self.request_handler: Optional[ServerBaseRequestHandler] = None

        self.request_counter = 0

    @staticmethod
    def get_instance():
        return ServerCommand.__instance

    def get_pretty_description_header(self) -> str:
        return f"{super().get_pretty_description_header()}"

    def create_argparse(self) -> argparse.ArgumentParser:
        parser = super().create_argparse()

        group = parser.add_argument_group("Server options")
        group.add_argument("-p", "--port", type=int, default=8080, help="The port to listen on")
        group.add_argument("-i", "--ip", type=str, default="0.0.0.0", help="The ip address to bind to")
        group.add_argument("-r", "--request-handler", type=str, default="simple_get", help="The request handler to use (default: simple_get)")
        group.add_argument("--prepare", type=int, default=0, help="Number of prepare artifacts to build ahead of time (default: 0)")

        return parser

    def parse_arguments(self, *args: str) -> Tuple[ServerOptions, argparse.ArgumentParser, argparse.Namespace]:
        parser = self.create_argparse()

        parsed_known_args = parser.parse_known_args(list(args))[0]
        target_request_handler = parsed_known_args.request_handler

        if target_request_handler not in REQUEST_HANDLERS:
            LOGGER.debug("Available request handlers:")
            for name in REQUEST_HANDLERS.keys():
                LOGGER.debug(f" - {name}")
            LOGGER.critical(f"Unknown request handler {target_request_handler}")

        self.request_handler = REQUEST_HANDLERS[target_request_handler]()
        assert isinstance(self.request_handler, ServerBaseRequestHandler), "Request handler must be a subclass of ServerBaseRequestHandler"

        self.request_handler.extend_argparse(parser)

        options, parser, args = super().parse_arguments(*args, parser=parser)
        options: ServerOptions = options

        options.request_handler = self.request_handler

        if args.port <= 0 or args.port > 65535:
            LOGGER.critical(f"Port {args.port} is not a valid port number")

        options.server_port = args.port

        ip = None
        try:
            ip = ip_address(args.ip)
        except ValueError:
            LOGGER.critical(f"Invalid ip: {args.ip}")
        options.server_host = ip

        options.num_artifacts_prepare = args.prepare

        self.request_handler.parse_arguments(args, options)

        return options, parser, args

    def execute(self, options: ServerOptions) -> bool:
        with self.__lock:
            ServerCommand.__instance = self

            LOGGER.info(f"Starting server on {options.server_host}:{options.server_port}")

            self.request_handler.initialize(self, options)

            class RequestHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    ServerCommand.get_instance().request_handler.handle_request(self, "GET")

                def do_POST(self):
                    ServerCommand.get_instance().request_handler.handle_request(self, "POST")

                def do_PUT(self):
                    ServerCommand.get_instance().request_handler.handle_request(self, "PUT")

                def do_DELETE(self):
                    ServerCommand.get_instance().request_handler.handle_request(self, "DELETE")

            class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
                pass

        try:
            with ThreadedHTTPServer((str(options.server_host), options.server_port), RequestHandler) as httpd:
                httpd.serve_forever()
        except KeyboardInterrupt:
            LOGGER.info("Stopping server")
            return True
        except OSError as e:
            LOGGER.critical(f"Port {options.server_port} is already in use.", e)
            return False

        raise NotImplementedError("Not implemented")

    def build(self, platform: Platform, arch: Architecture, artifact: str) -> Optional[bytes]:
        with self.__lock:
            with self.__request_lock:
                self.request_counter += 1
                request_id = self.request_counter

            LOGGER.info(f"Building request {request_id} for {platform.name} {arch.name} {artifact}")

            return f"Hello World {request_id}!".encode("utf-8")

