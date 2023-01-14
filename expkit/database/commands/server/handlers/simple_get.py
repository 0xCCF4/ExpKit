import argparse
import threading
import urllib
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse

from expkit.base.architecture import Platform, Architecture
from expkit.base.logger import get_logger
from expkit.database.commands.server.default import ServerOptions, ServerBaseRequestHandler, \
    register_server_request_parser

LOGGER = get_logger(__name__)


@register_server_request_parser("simple_get")
class SimpleGetHandler(ServerBaseRequestHandler):
    def __init__(self):
        super().__init__()
        self.__request_lock = threading.Lock()

    def extend_argparse(self, parser: argparse.ArgumentParser):
        group = parser.add_argument_group("Request Handler specific options")

        group.add_argument("--token", type=str, default=None, help="Token to authenticate requests (default: No token)")
        group.add_argument("--target", type=str, default=None, help="Default artifact to build (overrides url parameter)")

    def parse_arguments(self, args: argparse.Namespace, options: ServerOptions):
        options.request_handler_data["token"] = args.token
        options.request_handler_data["target"] = args.target

    def handle_request(self, handler: BaseHTTPRequestHandler, method: str):
        handler.protocol_version = "HTTP/1.1"
        url = urlparse(handler.path)
        query = urllib.parse.parse_qs(url.query)

        with self.__request_lock:
            LOGGER.info(f"Received request")
            LOGGER.info(f"   URL: {url.path}")
            LOGGER.info(f"   Query: {query}")
            LOGGER.info(f"   IP: {handler.client_address[0]}")
            LOGGER.info(f"   Port: {handler.client_address[1]}")
            LOGGER.info(f"   Method: {method}")

        if method != "GET":
            LOGGER.error(f"Invalid method: {method}")
            handler.send_response(405)
            handler.end_headers()
            return

        platform = query.get("os", ["DUMMY"])[0]
        arch = query.get("arch", [None])[0]
        target = query.get("target", [None])[0]
        token = query.get("token", [None])[0]

        if self.options.request_handler_data["target"] is not None:
            target = self.options.request_handler_data["target"]

        if self.options.request_handler_data["token"] is not None and token != self.options.request_handler_data["token"]:
            LOGGER.error(f"Invalid token: {token}")
            handler.send_response(401)
            handler.end_headers()
            return

        platform = Platform.get_platform_from_name(platform)
        if platform is Platform.UNKNOWN or not platform.is_single():
            LOGGER.error(f"Invalid platform: {platform}")
            handler.send_response(400)
            handler.end_headers()
            return

        if arch is None:
            arch = platform.supporting_architectures()[0].name
        arch = Architecture.get_architecture_from_name(arch)
        if arch is Architecture.UNKNOWN or not arch.is_single():
            LOGGER.error(f"Invalid architecture: {arch}")
            handler.send_response(400)
            handler.end_headers()
            return

        handler.send_response(200)
        handler.send_header("Content-type", "text/plain")
        handler.send_header(f"Keep-Alive", f"timeout={60 * 30}, max=1")  # 30 minutes
        handler.end_headers()

        response = self.server_cmd.build(platform, arch, target)
        handler.wfile.write(response)
        handler.wfile.flush()
