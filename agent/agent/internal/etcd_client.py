import random
from typing import override

import grpc
from etcd3 import Endpoint, MultiEndpointEtcd3Client, Transactions, etcdrpc

"""
The provided classes has been overridden to support multiple endpoints.
Also to support insecure connections for development purposes.
"""

class CustomMultiEndpointEtcd3Client(MultiEndpointEtcd3Client):
    @override
    def __init__(self, endpoints:list[Endpoint]=None, timeout=None, user=None, password=None,
                 failover=False, secure=False):
        self.metadata = None
        self.failover = failover

        # Cache GRPC stubs here
        self._stubs = {}

        # Step 1: setup endpoints
        self.endpoints = {ep.netloc: ep for ep in endpoints}
        self._current_endpoint_label = random.choice(
            list(self.endpoints.keys())
        )

        # Step 2: if auth is enabled, call the auth endpoint
        self.timeout = timeout
        self.call_credentials = None
        cred_params = [c is not None for c in (user, password)]

        if all(cred_params):
            auth_request = etcdrpc.AuthenticateRequest(
                name=user,
                password=password
            )

            resp = self.authstub.Authenticate(auth_request, self.timeout)
            self.metadata = (('token', resp.token),)
            if secure:
                self.call_credentials = grpc.ssl_channel_credentials()

        elif any(cred_params):
            raise Exception(
                'if using authentication credentials both user and password '
                'must be specified.'
            )

        self.transactions = Transactions()


class Etcd3Client(CustomMultiEndpointEtcd3Client):
    def __init__(self, addresses:list[str], ca_cert=None,
                 cert_key=None, cert_cert=None, timeout=None, user=None,
                 password=None, grpc_options=None):

        # Step 1: verify credentials
        cert_params = [c is not None for c in (cert_cert, cert_key)]
        if ca_cert is not None:
            if all(cert_params):
                credentials = self.get_secure_creds(
                    ca_cert,
                    cert_key,
                    cert_cert
                )
                self.uses_secure_channel = True
            elif any(cert_params):
                # some of the cert parameters are set
                raise ValueError(
                    'to use a secure channel ca_cert is required by itself, '
                    'or cert_cert and cert_key must both be specified.')
            else:
                credentials = self.get_secure_creds(ca_cert, None, None)
                self.uses_secure_channel = True
        else:
            self.uses_secure_channel = False
            credentials = None

        # Step 2: create Endpoints
        eps = []
        for addr in addresses:
            host, port = addr.split(':')
            port = int(port)
            ep = Endpoint(host, port, secure=self.uses_secure_channel,
                          creds=credentials, opts=grpc_options)
            eps.append(ep)

        super(Etcd3Client, self).__init__(
            endpoints=eps,
            timeout=timeout,
            user=user,
            password=password,
            secure=self.uses_secure_channel
        )


