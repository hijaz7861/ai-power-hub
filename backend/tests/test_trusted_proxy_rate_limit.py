
from types import SimpleNamespace
from starlette.requests import Request

from backend.app.core.rate_limit import _client_ip


def _request_from_peer(peer: str, forwarded: str) -> Request:
    return Request({
        "type": "http",
        "method": "POST",
        "path": "/api/v1/auth/login",
        "headers": [(b"x-forwarded-for", forwarded.encode("ascii"))],
        "client": (peer, 12345),
        "server": ("api", 8000),
        "scheme": "http",
        "query_string": b"",
    })


def test_forwarded_ip_is_used_only_when_direct_peer_is_trusted():
    trusted_settings = SimpleNamespace(trusted_proxy_ips="10.20.0.0/16")
    trusted_request = _request_from_peer("10.20.1.5", "198.51.100.44, 10.20.1.1")
    assert _client_ip(trusted_request, trusted_settings) == "198.51.100.44"

    untrusted_request = _request_from_peer("192.0.2.5", "198.51.100.44")
    assert _client_ip(untrusted_request, trusted_settings) == "192.0.2.5"


def test_invalid_forwarded_ip_is_rejected_for_trusted_proxy():
    settings = SimpleNamespace(trusted_proxy_ips="10.20.0.0/16")
    request = _request_from_peer("10.20.1.5", "not-an-ip")
    assert _client_ip(request, settings) is None
