import asyncio
import os
import ssl
import traceback
from typing import Optional, Tuple
from urllib.parse import unquote, urlparse

from codegate.ca.codegate_ca import CertificateAuthority
from codegate.utils.proxy import ProxyUtils
from codegate.config import Config
from codegate.providers.github.gh_logging import logger
from codegate.providers.github.gh_routes import GitHubRoutes

# Increase buffer sizes
MAX_BUFFER_SIZE = 10 * 1024 * 1024  # 10MB
CHUNK_SIZE = 64 * 1024  # 64KB

class ProxyProtocol(asyncio.Protocol):
    def __init__(self, loop):
        logger.info("Creating new ProxyProtocol instance")
        try:
            self.loop = loop
            self.transport: Optional[asyncio.Transport] = None
            self.target_transport: Optional[asyncio.Transport] = None
            self.peername: Optional[Tuple[str, int]] = None
            self.buffer = bytearray()
            self.target_host: Optional[str] = None
            self.target_port: Optional[int] = None
            self.handshake_done = False
            self.is_connect = False
            self.content_length = 0
            self.headers_parsed = False
            self.method = None
            self.path = None
            self.version = None
            self.headers = []
            self.target = None
            self.original_path = None
            self.ssl_context = None
            self.decrypted_data = bytearray()
            logger.info("Initializing CertificateAuthority in ProxyProtocol")
            self.ca = CertificateAuthority()
            self._cleanup_tasks = set()
        except Exception as e:
            logger.error(f"Error in ProxyProtocol: {e}")

    def connection_made(self, transport: asyncio.Transport):
        logger.info("Connection made to proxy")
        try:
            self.transport = transport
            self.peername = transport.get_extra_info('peername')
            logger.info(f"Client connected from {self.peername}")
            
            # Log connection details
            socket = transport.get_extra_info('socket')
            if socket:
                logger.info(f"Socket: family={socket.family}, type={socket.type}, proto={socket.proto}")
            
            # Log SSL info if available
            ssl_object = transport.get_extra_info('ssl_object')
            if ssl_object:
                logger.info(f"SSL version: {ssl_object.version()}")
                logger.info(f"Cipher: {ssl_object.cipher()}")
                logger.info(f"Peer certificate: {ssl_object.getpeercert()}")
            else:
                logger.info("No SSL object available yet")
        except Exception as e:
            logger.error(f"Error in connection_made: {e}")
            logger.error(traceback.format_exc())

    def connection_lost(self, exc):
        logger.info(f"Client disconnected from {self.peername}")
        try:
            # Cancel any pending tasks
            for task in self._cleanup_tasks:
                if not task.done():
                    task.cancel()

            # Close target transport if it exists
            if self.target_transport and not self.target_transport.is_closing():
                logger.info("Closing target transport")
                self.target_transport.close()

            # Close our transport if it exists
            if self.transport and not self.transport.is_closing():
                logger.info("Closing client transport")
                self.transport.close()

            # Clear any buffers
            self.buffer.clear()
            self.decrypted_data.clear()

            if exc:
                logger.error(f"Connection lost with error: {exc}")
                logger.error(traceback.format_exc())
            else:
                logger.info("Connection closed cleanly")
        except Exception as e:
            logger.error(f"Error in connection_lost: {e}")
            logger.error(traceback.format_exc())

    def data_received(self, data: bytes):
        logger.info(f"Received {len(data)} bytes of data")
        try:
            if len(self.buffer) + len(data) > MAX_BUFFER_SIZE:
                logger.error("Request too large")
                self.send_error_response(413, b"Request body too large")
                return

            self.buffer.extend(data)
            logger.debug(f"Current buffer size: {len(self.buffer)} bytes")

            if not self.headers_parsed:
                self.headers_parsed = self.parse_headers()
                if not self.headers_parsed:
                    logger.debug("Headers not fully received yet")
                    return

                if self.method == 'CONNECT':
                    logger.info("Handling CONNECT request")
                    self.handle_connect()
                else:
                    logger.info("Handling regular HTTP request")
                    task = asyncio.create_task(self.handle_http_request())
                    self._cleanup_tasks.add(task)
                    task.add_done_callback(self._cleanup_tasks.discard)
            elif self.target_transport and not self.target_transport.is_closing():
                logger.debug("Forwarding data to target")
                self.target_transport.write(data)
            else:
                logger.warning("No target transport available for data forwarding")

        except Exception as e:
            logger.error(f"Error in data_received: {e}")
            logger.error(traceback.format_exc())
            self.send_error_response(502, str(e).encode())

    async def handle_http_request(self):
        logger.debug(f"Method: {self.method}")
        try:
            logger.info(f"%%%%%%%%%%%%%%% Path:  %%%%%%%%%%%%%%%### {self.path}")
            try:
                target_url = await self.proxyutils.get_target_url(self.path)
            except Exception as e:
                logger.error(f"Get Target URL {e}")
            if not target_url:
                self.send_error_response(404, b"Not Found")
                return
            logger.info(f"target URL {target_url}")

            parsed_url = urlparse(target_url)
            logger.info(f"Parsed URL {parsed_url}")
            self.target_host = parsed_url.hostname
            self.target_port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)

            target_protocol = ProxyTargetProtocol(self)
            await self.loop.create_connection(
                lambda: target_protocol,
                self.target_host,
                self.target_port,
                ssl=parsed_url.scheme == 'https'
            )

            has_host = False
            new_headers = []
            for header in self.headers:
                if header.lower().startswith('host:'):
                    has_host = True
                    new_headers.append(f"Host: {self.target_host}")
                else:
                    new_headers.append(header)

            if not has_host:
                new_headers.append(f"Host: {self.target_host}")

            request_line = f"{self.method} /{self.path} {self.version}\r\n".encode()
            header_block = '\r\n'.join(new_headers).encode()
            headers = request_line + header_block + b'\r\n\r\n'

            if self.target_transport:
                logger.info("Sending request to target")
                self.target_transport.write(headers)

                # Forward body if present
                body_start = self.buffer.index(b'\r\n\r\n') + 4
                body = self.buffer[body_start:]
                if body:
                    logger.info(f"Forwarding {len(body)} bytes of request body")
                    self.target_transport.write(body)
            else:
                logger.error("Target transport not available")
                self.send_error_response(502, b"Failed to establish target connection")

        except Exception as e:
            logger.error(f"Error handling HTTP request: {e}")
            logger.error(traceback.format_exc())
            self.send_error_response(502, str(e).encode())

    def handle_connect(self):
        logger.info("Handling CONNECT request")
        try:
            path = unquote(self.target)
            if ':' in path:
                self.target_host, port = path.split(':')
                self.target_port = int(port)
                logger.info(f"CONNECT request to {self.target_host}:{self.target_port}")
                logger.info("Request headers:")
                for header in self.headers:
                    logger.info(f"  {header}")

                cert_path, key_path = self.ca.get_domain_certificate(self.target_host)
                logger.info(f"Using certificate: {cert_path}")
                logger.info(f"Using key: {key_path}")

                self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                self.ssl_context.load_cert_chain(cert_path, key_path)
                sself.ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
                # self.ssl_context.verify_mode = ssl.CERT_NONE
                # self.ssl_context.check_hostname = False
                logger.info("Created SSL context for CONNECT")

                self.is_connect = True
                task = asyncio.create_task(self.connect_to_target())
                self._cleanup_tasks.add(task)
                task.add_done_callback(self._cleanup_tasks.discard)
                self.handshake_done = True
            else:
                logger.error(f"Invalid CONNECT path: {path}")
                self.send_error_response(400, b"Invalid CONNECT path")
        except Exception as e:
            logger.error(f"Error handling CONNECT: {e}")
            logger.error(traceback.format_exc())
            self.send_error_response(502, str(e).encode())

    async def connect_to_target(self):
        logger.info("Connecting to target")
        try:
            if not self.target_host or not self.target_port:
                raise ValueError("Target host and port not set")

            logger.info(f"Creating connection to {self.target_host}:{self.target_port}")

            # Create SSL context for target connection
            target_ssl_context = ssl.create_default_context()
            target_ssl_context.check_hostname = False
            target_ssl_context.verify_mode = ssl.CERT_NONE
            logger.info("Created target SSL context")

            # Connect directly to target host
            target_protocol = ProxyTargetProtocol(self)
            transport, _ = await self.loop.create_connection(
                lambda: target_protocol,
                self.target_host,
                self.target_port,
                ssl=target_ssl_context
            )
            logger.info("Connected to target")

            # Send 200 Connection Established
            if self.transport and not self.transport.is_closing():
                logger.info("Sending Connection Established response")
                self.transport.write(
                    b'HTTP/1.1 200 Connection Established\r\n'
                    b'Proxy-Agent: ProxyPilot\r\n'
                    b'Connection: keep-alive\r\n\r\n'
                )

                # Upgrade client connection to SSL
                logger.info("Starting TLS handshake")
                transport = await self.loop.start_tls(
                    self.transport,
                    self,
                    self.ssl_context,
                    server_side=True
                )
                self.transport = transport
                logger.info("TLS handshake complete")

        except Exception as e:
            logger.error(f"Failed to connect to target {self.target_host}:{self.target_port}: {e}")
            logger.error(traceback.format_exc())
            self.send_error_response(502, str(e).encode())

    def send_error_response(self, status: int, message: bytes):
        try:
            response = (
                f"HTTP/1.1 {status} {self.get_status_text(status)}\r\n"
                f"Content-Length: {len(message)}\r\n"
                f"Content-Type: text/plain\r\n"
                f"\r\n"
            ).encode() + message
            if self.transport and not self.transport.is_closing():
                logger.info(f"Sending error response: {status}")
                self.transport.write(response)
                self.transport.close()
        except Exception as e:
            logger.error(f"Error sending error response: {e}")
            logger.error(traceback.format_exc())

    def get_status_text(self, status: int) -> str:
        status_texts = {
            400: "Bad Request",
            404: "Not Found",
            413: "Request Entity Too Large",
            502: "Bad Gateway"
        }
        return status_texts.get(status, "Error")

class ProxyTargetProtocol(asyncio.Protocol):
    def __init__(self, proxy: ProxyProtocol):
        self.proxy = proxy
        self.transport: Optional[asyncio.Transport] = None
        self._buffer = bytearray()

    def connection_made(self, transport: asyncio.Transport):
        logger.info("Target connection made")
        self.transport = transport
        self.proxy.target_transport = transport

    def data_received(self, data: bytes):
        logger.info(f"Received {len(data)} bytes from target")
        if self.proxy.transport and not self.proxy.transport.is_closing():
            self.proxy.transport.write(data)
        else:
            # Buffer data if transport is not ready
            if len(self._buffer) + len(data) <= MAX_BUFFER_SIZE:
                self._buffer.extend(data)
                logger.debug(f"Buffered {len(data)} bytes from target")

    def connection_lost(self, exc):
        logger.info("Target connection lost")
        try:
            # Clear any buffered data
            self._buffer.clear()

            # Close proxy transport if it exists
            if self.proxy.transport and not self.proxy.transport.is_closing():
                logger.info("Closing proxy transport")
                self.proxy.transport.close()

            # Close our transport if it exists
            if self.transport and not self.transport.is_closing():
                logger.info("Closing target transport")
                self.transport.close()

            if exc:
                logger.error(f"Target connection lost with error: {exc}")
                logger.error(traceback.format_exc())
            else:
                logger.info("Target connection closed cleanly")
        except Exception as e:
            logger.error(f"Error in target connection_lost: {e}")
            logger.error(traceback.format_exc())

async def create_proxy_server(host: str, port: int, ssl_context: Optional[ssl.SSLContext] = None):
    logger.info(f"Creating proxy server on {host}:{port}")
    if ssl_context:
        logger.info("SSL context provided")
        logger.info(f"SSL version: {ssl_context.minimum_version}")
        logger.info(f"Verify mode: {ssl_context.verify_mode}")
        logger.info(f"Check hostname: {ssl_context.check_hostname}")
    
    loop = asyncio.get_event_loop()

    def create_protocol():
        return ProxyProtocol(loop)

    server = await loop.create_server(
        create_protocol,
        host,
        port,
        ssl=ssl_context,
        reuse_port=True,
        start_serving=True
    )

    logger.info(f"Proxy server running on {host}:{port}")
    return server

async def run_proxy_server():
    logger.info("Starting proxy server")
    try:
        
        ca = CertificateAuthority()
        ca.ensure_certificates_exist()
        ssl_context = ca.create_ssl_context()

        server = await create_proxy_server(
            Config.get_config().host,
            Config.get_config().proxy_port,
            ssl_context
        )
        # Initialize config first
        config = Config.get_config()
        if not config:
            raise RuntimeError("Configuration not initialized")
        logger.info(f"Using config: {config}")

        # Create certs directory if it doesn't exist
        if not os.path.exists(config.certs_dir):
            logger.info(f"Creating certificates directory: {config.certs_dir}")
            os.makedirs(config.certs_dir)

        # Initialize CA and ensure certificates exist
        logger.info("Initializing CertificateAuthority")
        
        

        # Create SSL context after ensuring certs exist
        logger.info("Creating SSL context")
        ssl_context = ca.get_ssl_context()
        logger.info("SSL context created")

        # Create and run the proxy server
        logger.info("Creating proxy server")
        server = await create_proxy_server(
            config.host,
            config.proxy_port,
            ssl_context
        )

        logger.info("Starting server")
        async with server:
            await server.serve_forever()

    except Exception as e:
        logger.error(f"Proxy server error: {e}")
        logger.error(traceback.format_exc())
        raise
