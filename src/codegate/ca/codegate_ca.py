import datetime
import os
import ssl
from typing import Dict, Tuple

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from codegate.config import Config


class CertificateAuthority:
    def __init__(self):
        self._ca_cert = None
        self._ca_key = None
        self._cert_cache: Dict[str, Tuple[str, str]] = {}
        self._load_or_generate_ca()

    def _load_or_generate_ca(self):
        """Load existing CA certificate and key or generate new ones"""
        ca_cert_path = os.path.join(Config.get_config().certs_dir, "ca.crt")
        ca_key_path = os.path.join(Config.get_config().certs_dir, "ca.key")

        if os.path.exists(ca_cert_path) and os.path.exists(ca_key_path):
            # Load existing CA certificate and key
            with open(ca_cert_path, "rb") as f:
                self._ca_cert = x509.load_pem_x509_certificate(f.read())
            with open(ca_key_path, "rb") as f:
                self._ca_key = serialization.load_pem_private_key(f.read(), password=None)
        else:
            # Generate new CA certificate and key
            self._ca_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=4096,
            )

            name = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, "Proxy Pilot CA"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Proxy Pilot"),
                x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Development"),
                x509.NameAttribute(NameOID.COUNTRY_NAME, "UK"),
            ])

            builder = x509.CertificateBuilder()
            builder = builder.subject_name(name)
            builder = builder.issuer_name(name)
            builder = builder.public_key(self._ca_key.public_key())
            builder = builder.serial_number(x509.random_serial_number())
            builder = builder.not_valid_before(datetime.datetime.utcnow())
            builder = builder.not_valid_after(
                datetime.datetime.utcnow() + datetime.timedelta(days=3650)  # 10 years
            )

            builder = builder.add_extension(
                x509.BasicConstraints(ca=True, path_length=None),
                critical=True,
            )

            builder = builder.add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    content_commitment=False,
                    key_encipherment=True,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=True,  # This is a CA
                    crl_sign=True,
                    encipher_only=False,
                    decipher_only=False
                ),
                critical=True,
            )

            self._ca_cert = builder.sign(
                private_key=self._ca_key,
                algorithm=hashes.SHA256(),
            )

            # Save CA certificate and key
            if not os.path.exists(Config.get_config().certs_dir):
                os.makedirs(Config.get_config().certs_dir)

            with open(ca_cert_path, "wb") as f:
                f.write(self._ca_cert.public_bytes(serialization.Encoding.PEM))

            with open(ca_key_path, "wb") as f:
                f.write(self._ca_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))

    def get_domain_certificate(self, domain: str) -> Tuple[str, str]:
        """Get or generate a certificate for a specific domain"""
        if domain in self._cert_cache:
            return self._cert_cache[domain]

        # Generate new certificate for domain
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,  # 2048 bits is sufficient for domain certs
        )

        name = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, domain),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Proxy Pilot Generated"),
        ])

        builder = x509.CertificateBuilder()
        builder = builder.subject_name(name)
        builder = builder.issuer_name(self._ca_cert.subject)
        builder = builder.public_key(key.public_key())
        builder = builder.serial_number(x509.random_serial_number())
        builder = builder.not_valid_before(datetime.datetime.utcnow())
        builder = builder.not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=365)
        )

        # Add domain to SAN
        builder = builder.add_extension(
            x509.SubjectAlternativeName([x509.DNSName(domain)]),
            critical=False,
        )

        # Add extended key usage
        builder = builder.add_extension(
            x509.ExtendedKeyUsage([
                ExtendedKeyUsageOID.SERVER_AUTH,
                ExtendedKeyUsageOID.CLIENT_AUTH,
            ]),
            critical=False,
        )

        # Basic constraints (not a CA)
        builder = builder.add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )

        certificate = builder.sign(
            private_key=self._ca_key,
            algorithm=hashes.SHA256(),
        )

        # Save certificate and key
        cert_path = os.path.join(Config.get_config().ca_cert_path, f"{domain}.crt")
        key_path = os.path.join(Config.get_config().ca_cert_path, f"{domain}.key")

        with open(cert_path, "wb") as f:
            f.write(certificate.public_bytes(serialization.Encoding.PEM))

        with open(key_path, "wb") as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))

        self._cert_cache[domain] = (cert_path, key_path)
        return cert_path, key_path

    def generate_certificates(self) -> Tuple[str, str]:
        """Generate self-signed certificates with proper extensions for HTTPS proxy"""
        # Create certificates directory if it doesn't exist
        if not os.path.exists(Config.get_config().certs_dir):
            os.makedirs(Config.get_config().certs_dir)

        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
        )

        # Generate public key
        public_key = private_key.public_key()

        # Create certificate builder
        builder = x509.CertificateBuilder()

        # Add name attributes
        name = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "Proxy Pilot CA"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Proxy Pilot"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Development"),
            x509.NameAttribute(NameOID.COUNTRY_NAME, "UK"),
        ])

        # Basic certificate information
        builder = builder.subject_name(name)
        builder = builder.issuer_name(name)
        builder = builder.public_key(public_key)
        builder = builder.serial_number(x509.random_serial_number())
        builder = builder.not_valid_before(datetime.datetime.utcnow())
        builder = builder.not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=365)
        )

        # Add key usage extensions
        builder = builder.add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False
            ),
            critical=True,
        )

        # Add extended key usage extension
        builder = builder.add_extension(
            x509.ExtendedKeyUsage([
                ExtendedKeyUsageOID.SERVER_AUTH,
                ExtendedKeyUsageOID.CLIENT_AUTH,
                ExtendedKeyUsageOID.CODE_SIGNING,
                ExtendedKeyUsageOID.EMAIL_PROTECTION,
            ]),
            critical=False,
        )

        # Add basic constraints extension
        builder = builder.add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        )

        # Add key identifier extensions
        builder = builder.add_extension(
            x509.SubjectKeyIdentifier.from_public_key(public_key),
            critical=False,
        )

        builder = builder.add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(public_key),
            critical=False,
        )

        # Sign the certificate
        certificate = builder.sign(
            private_key=private_key,
            algorithm=hashes.SHA256(),
        )

        # Write private key
        key_path = os.path.join(Config.get_config().certs_dir, "server.key")
        with open(key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))

        # Write certificate
        cert_path = os.path.join(Config.get_config().certs_dir, "server.crt")
        with open(cert_path, "wb") as f:
            f.write(certificate.public_bytes(serialization.Encoding.PEM))

        print("Certificates generated successfully in the 'certs' directory")
        print("\nTo trust these certificates:")
        print("\nOn macOS:")
        print("sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain certs/server.crt")
        print("\nOn Windows (PowerShell as Admin):")
        print("Import-Certificate -FilePath \"certs\\server.crt\" -CertStoreLocation Cert:\\LocalMachine\\Root")
        print("\nOn Linux:")
        print("sudo cp certs/server.crt /usr/local/share/ca-certificates/proxy-pilot.crt")
        print("sudo update-ca-certificates")
        print("\nFor VSCode, add to settings.json:")
        print('''{
        "http.proxy": "https://localhost:8989",
        "http.proxySupport": "on",
        "github.copilot.advanced": {
            "debug.testOverrideProxyUrl": "https://localhost:8989",
            "debug.overrideProxyUrl": "https://localhost:8989"
        }
    }''')

        return cert_path, key_path

    def create_ssl_context(self) -> ssl.SSLContext:
        """Create SSL context with secure configuration"""
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(Config.get_config().ca_cert_file, Config.get_config().ca_key_file)
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
        ssl_context.options |= (
            ssl.OP_NO_SSLv2 |
            ssl.OP_NO_SSLv3 |
            ssl.OP_NO_COMPRESSION |
            ssl.OP_CIPHER_SERVER_PREFERENCE
        )
        ssl_context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20')
        return ssl_context

    def ensure_certificates_exist(self) -> None:
        """Ensure SSL certificates exist, generate if they don't"""
        print("Checking certs")
        if not (os.path.exists(Config.get_config().server_cert_file) and os.path.exists(Config.get_config().server_key_file)):
            self.generate_certificates()

    def get_ssl_context(self) -> ssl.SSLContext:
        """Get SSL context with certificates"""
        self.ensure_certificates_exist()
        return self.create_ssl_context()

    def get_cert_files() -> Tuple[str, str]:
        """Get certificate and key file paths"""
        return Config.get_config().server_cert_file, Config.get_config().server_key_file

