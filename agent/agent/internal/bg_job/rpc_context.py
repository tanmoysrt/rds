
import grpc


class DummyRPCContext(grpc.ServicerContext):
    """
    We will reuse the grpc functions in running jobs
    GRPC handlers expect a request and context object.

    This dummy context object will be used to simulate the context
    In most of the cases, it has no use, but it is required to satisfy the grpc handler signature.
    """
    def abort(self, code, details):
        raise grpc.RpcError(details)

    def abort_with_status(self, status):
        raise grpc.RpcError(status.details)

    def set_code(self, code): pass
    def set_details(self, details): pass
    def is_active(self): return True
    def time_remaining(self): return None
    def add_callback(self, callback): return True
    def invocation_metadata(self): return []
    def peer(self): return "dummy-peer"
    def peer_identities(self): return []
    def peer_identity_key(self): return ""
    def auth_context(self): return {}
    def set_compression(self, compression_algorithm): pass
    def cancel(self): pass

    # These are required for Python >= 3.10
    def send_initial_metadata(self, initial_metadata): pass
    def set_trailing_metadata(self, trailing_metadata): pass
    def trailing_metadata(self): return []
