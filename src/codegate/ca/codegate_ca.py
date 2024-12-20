import os
import ssl
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple

import structlog
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from codegate.config import Config

logger = structlog.get_logger("codegate")

# Add a buffer to renew certificates slightly before expiry.
TLS_GRACE_PERIOD_DAYS = 2


@dataclass
class CachedCertificate:
    """Hold certificate data with metadata"""

    cert_path: str
    key_path: str
    creation_time: datetime


class TLSCertDomainManager:
    """
    This class manages SSL contexts for domain certificates with SNI
    """

    def __init__(self, ca_provider: "CertificateAuthority"):
        self._ca = ca_provider
        # Use strong references for caching
        self._cert_cache: Dict[str, CachedCertificate] = {}
        self._context_cache: Dict[str, ssl.SSLContext] = {}

    def get_domain_context(self, server_name: str) -> ssl.SSLContext:
        cert_path, key_path = self._ca.get_domain_certificate(server_name)
        context = self._create_domain_ssl_context(cert_path, key_path, server_name)
        return context

    def _create_domain_ssl_context(
        self, cert_path: str, key_path: str, domain: str
    ) -> ssl.SSLContext:
        """
        Domain SNI Context Setting
        """

        logger.debug(f"Loading cert chain from {cert_path} for domain {domain}")
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        try:
            context.load_cert_chain(cert_path, key_path)
        except ssl.SSLError as e:
            logger.error(f"Failed to load cert chain for {domain}: {e}")
            raise

        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.set_ciphers("ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20")
        context.options |= (
            ssl.OP_NO_SSLv2
            | ssl.OP_NO_SSLv3
            | ssl.OP_NO_COMPRESSION
            | ssl.OP_CIPHER_SERVER_PREFERENCE
        )
        return context


class CertificateAuthority:
    """
    Singleton class for Certificate Authority management.
    Access the instance using CertificateAuthority.get_instance()
    """

    _instance: Optional["CertificateAuthority"] = None

    @classmethod
    def get_instance(cls) -> "CertificateAuthority":
        """Get or create the singleton instance of CertificateAuthority"""
        if cls._instance is None:
            logger.debug("Creating new CertificateAuthority instance")
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        """
        Initialize the Certificate Authority.
        Note: Use get_instance() instead of creating a new instance directly.
        """
        if CertificateAuthority._instance is not None:
            raise RuntimeError("Use CertificateAuthority.get_instance() instead")

        logger.debug("Initializing Certificate Authority class: CertificateAuthority")
        self._ca_cert = None
        self._ca_key = None
        self._ca_cert_expiry = None
        self._ca_last_load_time = None

        # Use strong references for caching certificates
        self._cert_cache: Dict[str, CachedCertificate] = {}
        # Use a separate cache for SSL contexts
        self._context_cache: Dict[str, Tuple[ssl.SSLContext, datetime]] = {}

        CertificateAuthority._instance = self

        # Load existing certificates into cache
        self._load_existing_certificates()

    def _load_existing_certificates(self) -> None:
        """Load existing certificates from disk into the cache."""
        logger.debug("Loading existing certificates from disk into cache")
        certs_dir = Config.get_config().certs_dir

        if not os.path.exists(certs_dir):
            logger.debug(f"Certificates directory {certs_dir} does not exist")
            return

        # First load the CA certificate to verify signatures
        try:
            ca_cert_path = self.get_cert_path(Config.get_config().ca_cert)
            logger.debug(f"Loading CA certificate for verification: {ca_cert_path}")
            with open(ca_cert_path, "rb") as f:
                ca_cert = x509.load_pem_x509_certificate(f.read(), default_backend())
        except Exception as e:
            logger.error(f"Failed to load CA certificate for verification: {e}")
            return

        # Get current time for expiry checks
        current_time = datetime.now(timezone.utc)
        expiry_date = current_time + timedelta(days=TLS_GRACE_PERIOD_DAYS)

        for filename in os.listdir(certs_dir):
            if (
                filename.endswith('.crt') and
                filename not in [Config.get_config().ca_cert, Config.get_config().server_cert]
            ):
                cert_path = os.path.join(certs_dir, filename)
                key_path = os.path.join(certs_dir, filename.replace('.crt', '.key'))

                # Skip if key file doesn't exist
                if not os.path.exists(key_path):
                    logger.debug(f"Skipping {filename} as key file does not exist")
                    continue

                try:
                    # Load and validate certificate
                    with open(cert_path, "rb") as cert_file:
                        cert = x509.load_pem_x509_certificate(cert_file.read(), default_backend())

                    # Extract domain from common name
                    common_name = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value

                    # Verify certificate is signed by our CA
                    try:
                        ca_cert.public_key().verify(
                            cert.signature,
                            cert.tbs_certificate_bytes,
                            padding.PKCS1v15(),
                            cert.signature_hash_algorithm,
                        )
                    except InvalidSignature:
                        logger.debug(f"Skipping {filename} as it's not signed by our CA")
                        continue

                    # Check if certificate is still valid
                    if cert.not_valid_after_utc > expiry_date:
                        logger.debug(f"Loading valid certificate for {common_name}")
                        self._cert_cache[common_name] = CachedCertificate(
                            cert_path=cert_path,
                            key_path=key_path,
                            creation_time=datetime.utcnow(),
                        )
                    else:
                        logger.debug(f"Skipping expired certificate for {common_name}")

                except Exception as e:
                    logger.error(f"Failed to load certificate {filename}: {e}")
                    continue

        logger.debug(f"Loaded {len(self._cert_cache)} certificates into cache")

    def _get_cached_ca_certificates(self) -> Tuple[x509.Certificate, rsa.RSAPrivateKey]:
        """Get CA certificates from cache or load them if needed."""
        current_time = datetime.now(timezone.utc)

        # Check if certificates are loaded and not expired
        if (
            self._ca_cert is not None
            and self._ca_key is not None
            and self._ca_cert_expiry is not None
            and current_time < self._ca_cert_expiry
        ):
            return self._ca_cert, self._ca_key

        # Load certificates from disk
        logger.debug("Loading CA certificates from disk")
        ca_cert_path = self.get_cert_path(Config.get_config().ca_cert)
        ca_key_path = self.get_cert_path(Config.get_config().ca_key)

        try:
            with open(ca_cert_path, "rb") as f:
                self._ca_cert = x509.load_pem_x509_certificate(f.read(), default_backend())
                self._ca_cert_expiry = self._ca_cert.not_valid_after_utc

            with open(ca_key_path, "rb") as f:
                self._ca_key = serialization.load_pem_private_key(
                    f.read(), password=None, backend=default_backend()
                )

            self._ca_last_load_time = current_time
            logger.debug("Successfully loaded and cached CA certificates")
            return self._ca_cert, self._ca_key

        except Exception as e:
            logger.error(f"Failed to load CA certificates: {e}")
            # Clear cached values on error
            self._ca_cert = None
            self._ca_key = None
            self._ca_cert_expiry = None
            self._ca_last_load_time = None
            raise

    def remove_certificates(self) -> None:
        """Remove all cached certificates and contexts"""
        logger.debug("Removing all cached certificates and contexts")
        self.certs_dir = Config.get_config().certs_dir
        # remove and recreate certs directory
        try:
            logger.debug(f"Removing certs directory: {self.certs_dir}")
            os.rmdir(self.certs_dir)
            os.makedirs(self.certs_dir)
            # Clear CA certificate cache
            self._ca_cert = None
            self._ca_key = None
            self._ca_cert_expiry = None
            self._ca_last_load_time = None
        except OSError as e:
            logger.error(f"Failed to remove certs directory: {e}")
            raise

    def generate_ca_certificates(self) -> None:
        """
        Generate self-signed CA certificates

        Key Attributes are:
        X509v3
        Key Usage
        Digital Signature, Key Encipherment, Key Cert Sign, CRL Sign

        Expirtation:
        1 year from now

        """
        logger.debug("Generating CA certificates fn: generate_ca_certificates")

        # Generate private key
        logger.debug("Generating private key for CA")
        self._ca_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
        )

        logger.debug("Generating public key for CA")
        self._ca_public_key = self._ca_key.public_key()

        # Define certificate subject
        name = x509.Name(
            [
                x509.NameAttribute(NameOID.COMMON_NAME, "CodeGate CA"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "CodeGate"),
                x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "CodeGate"),
                x509.NameAttribute(NameOID.COUNTRY_NAME, "UK"),
            ]
        )

        # Create certificate builder
        builder = x509.CertificateBuilder()
        builder = builder.subject_name(name)
        builder = builder.issuer_name(name)
        builder = builder.public_key(self._ca_public_key)
        builder = builder.serial_number(x509.random_serial_number())
        builder = builder.not_valid_before(datetime.now(timezone.utc))
        builder = builder.not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))

        # Add basic constraints
        builder = builder.add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        )

        # Add key usage
        builder = builder.add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )

        # Sign the certificate
        logger.debug("Signing CA certificate")
        self._ca_cert = builder.sign(
            private_key=self._ca_key,
            algorithm=hashes.SHA256(),
        )

        # Set expiry time for cache
        self._ca_cert_expiry = self._ca_cert.not_valid_after_utc
        self._ca_last_load_time = datetime.now(timezone.utc)


        # Define file paths for certificate and key
        ca_cert_path = self.get_cert_path(Config.get_config().ca_cert)
        ca_key_path = self.get_cert_path(Config.get_config().ca_key)

        if not os.path.exists(Config.get_config().certs_dir):
            logger.debug(f"Creating directory: {Config.get_config().certs_dir}")
            os.makedirs(Config.get_config().certs_dir)

        with open(ca_cert_path, "wb") as f:
            logger.debug(f"Saving CA certificate to {ca_cert_path}")
            f.write(self._ca_cert.public_bytes(serialization.Encoding.PEM))

        with open(ca_key_path, "wb") as f:
            logger.debug(f"Saving CA key to {ca_key_path}")
            f.write(
                self._ca_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )

    def get_domain_certificate(self, domain: str) -> Tuple[str, str]:
        """Generate or retrieve a cached certificate for a domain."""
        logger.debug(f"Getting domain certificate for domain: {domain}")

        # Use cached CA certificates
        ca_cert, ca_key = self._get_cached_ca_certificates()

        cached = self._cert_cache.get(domain)
        if cached:
            # Validate the cached certificate's expiry
            try:
                with open(cached.cert_path, "rb") as domain_cert_file:
                    domain_cert = x509.load_pem_x509_certificate(
                        domain_cert_file.read(), default_backend()
                    )
                # Check if certificate is still valid beyond the grace period
                expiry_date = datetime.now(timezone.utc) + timedelta(days=TLS_GRACE_PERIOD_DAYS)
                logger.debug(f"Certificate expiry: {domain_cert.not_valid_after_utc}")
                if domain_cert.not_valid_after_utc > expiry_date:
                    logger.debug(
                        f"Using cached certificate for {domain} from {cached.cert_path}"
                    )  # noqa: E501
                    return cached.cert_path, cached.key_path
                else:
                    logger.debug(f"Cached certificate for {domain} is expiring soon, renewing.")
            except Exception as e:
                logger.error(f"Failed to validate cached certificate for {domain}: {e}")

        logger.debug(f"Generating new certificate for domain: {domain}")
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        # Nothing is in the cache or its expired, generate a new one!

        name = x509.Name(
            [
                x509.NameAttribute(NameOID.COMMON_NAME, domain),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "CodeGate Generated"),
            ]
        )

        builder = x509.CertificateBuilder()
        builder = builder.subject_name(name)
        builder = builder.issuer_name(ca_cert.subject)
        builder = builder.public_key(key.public_key())
        builder = builder.serial_number(x509.random_serial_number())
        builder = builder.not_valid_before(datetime.now(timezone.utc))
        builder = builder.not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
        builder = builder.add_extension(
            x509.SubjectAlternativeName([x509.DNSName(domain)]), critical=False
        )
        builder = builder.add_extension(
            x509.ExtendedKeyUsage(
                [ExtendedKeyUsageOID.SERVER_AUTH, ExtendedKeyUsageOID.CLIENT_AUTH]
            ),
            critical=False,
        )
        builder = builder.add_extension(
            x509.BasicConstraints(ca=False, path_length=None), critical=False
        )

        certificate = builder.sign(private_key=ca_key, algorithm=hashes.SHA256())

        cert_dir = Config.get_config().certs_dir
        domain_cert_path = os.path.join(cert_dir, f"{domain}.crt")
        domain_key_path = os.path.join(cert_dir, f"{domain}.key")

        try:
            os.makedirs(cert_dir, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create directory {cert_dir} for {domain}: {e}")
            raise

        try:
            logger.debug(f"Saving certificate to {domain_cert_path} for domain {domain}")
            with open(domain_cert_path, "wb") as f:
                f.write(certificate.public_bytes(serialization.Encoding.PEM))

            logger.debug(f"Saving key to {domain_key_path} for domain {domain}")
            with open(domain_key_path, "wb") as f:
                f.write(
                    key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption(),
                    )
                )
        except OSError as e:
            logger.error(f"Failed to save certificate or key for {domain}: {e}")
            raise

        logger.debug(f"Generated and cached new certificate for {domain}")
        return domain_cert_path, domain_key_path

    def load_ca_certificates(self) -> Tuple[x509.Certificate, rsa.RSAPrivateKey]:
        """Load CA certificates for HTTPS proxy"""
        logger.debug("Loading CA certificates fn: load_ca_certificates")
        return self._get_cached_ca_certificates()

    def generate_server_certificates(self) -> Tuple[x509.Certificate, rsa.RSAPrivateKey]:
        """Generate self-signed server certificates for HTTPS proxy"""
        logger.debug("Generating server certificates fn: generate_server_certificates")
        try:
            ca_cert, ca_key = self._get_cached_ca_certificates()
        except Exception as e:
            logger.error(f"Failed to load CA certificates: {e}")
            raise

        logger.debug("Generating private key for server")
        server_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        name = x509.Name(
            [
                x509.NameAttribute(NameOID.COMMON_NAME, "CodeGate Server"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "CodeGate"),
            ]
        )

        builder = x509.CertificateBuilder()
        builder = builder.subject_name(name)
        builder = builder.issuer_name(ca_cert.subject)
        builder = builder.public_key(server_key.public_key())
        builder = builder.serial_number(x509.random_serial_number())
        builder = builder.not_valid_before(datetime.now(timezone.utc))
        builder = builder.not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))

        builder = builder.add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost")]),
            critical=False,
        )

        builder = builder.add_extension(
            x509.ExtendedKeyUsage(
                [
                    ExtendedKeyUsageOID.SERVER_AUTH,
                    ExtendedKeyUsageOID.CLIENT_AUTH,
                ]
            ),
            critical=False,
        )

        builder = builder.add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=False,
        )

        logger.debug("Signing server certificate with CA")
        server_cert = builder.sign(
            private_key=ca_key,
            algorithm=hashes.SHA256(),
        )

        server_cert_path = os.path.join(
            Config.get_config().certs_dir, Config.get_config().server_cert
        )
        server_key_path = os.path.join(
            Config.get_config().certs_dir, Config.get_config().server_key
        )

        try:
            logger.debug(f"Saving server certificate to {server_cert_path}")
            with open(server_cert_path, "wb") as f:
                f.write(server_cert.public_bytes(serialization.Encoding.PEM))

            logger.debug(f"Saving server key to {server_key_path}")
            with open(server_key_path, "wb") as f:
                f.write(
                    server_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption(),
                    )
                )
        except OSError as e:
            logger.error(f"Failed to write server certificate or key: {e}")
            raise

        logger.debug("Server certificates generated successfully")
        return server_cert, server_key

    def create_server_ssl_context(self) -> ssl.SSLContext:
        """Create SSL context with secure configuration"""
        server_cert_path = self.get_cert_path(Config.get_config().server_cert)
        server_key_path = self.get_cert_path(Config.get_config().server_key)

        logger.debug("Creating SSL context fn: create_ssl_context")

        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

        logger.debug(f"Using server cert: {server_cert_path}")

        logger.debug(f"Using server cert: {server_key_path}")
        try:
            ssl_context.load_cert_chain(server_cert_path, server_key_path)
        except ssl.SSLError as e:
            logger.error(f"Failed to load cert chain: {e}")
            raise

        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
        ssl_context.options |= (
            ssl.OP_NO_SSLv2
            | ssl.OP_NO_SSLv3
            | ssl.OP_NO_COMPRESSION
            | ssl.OP_CIPHER_SERVER_PREFERENCE
        )
        ssl_context.set_ciphers("ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20")
        logger.debug("SSL context created successfully")
        return ssl_context

    def check_and_ensure_certificates(self) -> bool:
        """Check if SSL certificates exist, ensure their presence, and validate them."""

        logger.debug("Checking and ensuring SSL certificates exist: check_and_ensure_certificates")

        def is_certificate_valid(cert_path: str) -> bool:
            """Check if a certificate is valid (not expired) using cryptography."""
            try:
                with open(cert_path, "rb") as cert_file:
                    cert_data = cert_file.read()  # Read the certificate file
                    cert = x509.load_pem_x509_certificate(cert_data, default_backend())

                    # Use timezone-aware expiration date
                    expiration_date = cert.not_valid_after_utc
                    current_time = datetime.now(timezone.utc)
                    return expiration_date > current_time
            except Exception as e:
                logger.error(f"Failed to validate certificate {cert_path}: {e}")
                return False

        server_cert_path = self.get_cert_path(Config.get_config().server_cert)
        server_key_path = self.get_cert_path(Config.get_config().server_key)
        ca_cert_path = self.get_cert_path(Config.get_config().ca_cert)
        ca_key_path = self.get_cert_path(Config.get_config().ca_key)

        cert_status = {
            "server_cert": os.path.exists(server_cert_path)
            and is_certificate_valid(server_cert_path),
            "server_key": os.path.exists(server_key_path),
            "ca_cert": os.path.exists(ca_cert_path) and is_certificate_valid(ca_cert_path),
            "ca_key": os.path.exists(ca_key_path),
        }

        for cert_name, exists in cert_status.items():
            logger.debug(f"{cert_name} exists: {exists}")

        if all(cert_status.values()):
            return True

        if not cert_status["ca_cert"] or not cert_status["ca_key"]:
            logger.info(
                "CA certificates missing or invalid, generating new CA and server certificates."
            )
            # Clear the CA certificate cache before regenerating
            # with self._cache_lock:
            self._ca_cert = None
            self._ca_key = None
            self._ca_cert_expiry = None
            self._ca_last_load_time = None

            self.generate_ca_certificates()
            self.generate_server_certificates()

        elif not cert_status["server_cert"] or not cert_status["server_key"]:
            logger.info(
                "Server certificates missing or invalid, generating new server certificates."
            )
            self.generate_server_certificates()

        return False

    def get_cert_path(self, cert_name: str) -> str:
        logger.debug(f"Using path: {Config.get_config().certs_dir, cert_name}")
        return os.path.join(Config.get_config().certs_dir, cert_name)
