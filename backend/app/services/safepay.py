"""Safepay Express Checkout adapter.

Only the fixed Safepay sandbox/production hosts are selectable. Secrets remain
server-side. The adapter is mock-tested and must not be described as live until
merchant credentials and a real sandbox transaction are verified.
"""
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx


class SafepayError(RuntimeError):
    """Sanitised Safepay integration failure."""


@dataclass(frozen=True)
class SafepayCheckout:
    tracker: str
    checkout_url: str


class SafepayClient:
    HOSTS = {
        "sandbox": ("https://sandbox.api.getsafepay.com", "https://sandbox.api.getsafepay.com"),
        "production": ("https://api.getsafepay.com", "https://getsafepay.com"),
    }

    def __init__(
        self,
        *,
        api_key: str,
        secret_key: str,
        environment: str = "sandbox",
        timeout_seconds: float = 20.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if environment not in self.HOSTS:
            raise ValueError("Safepay environment must be sandbox or production")
        if not api_key.strip() or not secret_key.strip():
            raise ValueError("Safepay API and secret keys are required")
        if not 1 <= timeout_seconds <= 60:
            raise ValueError("timeout_seconds must be between 1 and 60")
        self.api_key = api_key
        self.secret_key = secret_key
        self.environment = environment
        self.api_base, self.checkout_base = self.HOSTS[environment]
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    async def create_checkout(
        self,
        *,
        amount_minor_units: int,
        currency: str,
        order_reference: str,
        public_app_url: str,
    ) -> SafepayCheckout:
        if isinstance(amount_minor_units, bool) or not isinstance(amount_minor_units, int) or amount_minor_units < 1:
            raise ValueError("amount_minor_units must be a positive integer")
        if currency != "PKR":
            raise ValueError("Only PKR is enabled for this initial Safepay integration")
        if not order_reference or len(order_reference) > 64:
            raise ValueError("order_reference is invalid")
        if not public_app_url.startswith("https://"):
            raise ValueError("PUBLIC_APP_URL must use HTTPS")

        headers = {
            "X-SFPY-MERCHANT-SECRET": self.secret_key,
            "content-type": "application/json",
        }
        try:
            async with httpx.AsyncClient(
                base_url=self.api_base,
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                session_response = await client.post(
                    "/order/payments/v3/",
                    headers=headers,
                    json={
                        "merchant_api_key": self.api_key,
                        "intent": "CYBERSOURCE",
                        "mode": "payment",
                        "entry_mode": "raw",
                        "currency": currency,
                        "amount": amount_minor_units,
                        "include_fees": False,
                        "metadata": {"order_id": order_reference, "source": "ai-power-hub"},
                    },
                )
                session_response.raise_for_status()
                session_data = session_response.json()
                tracker = session_data["data"]["tracker"]["token"]
                if not isinstance(tracker, str) or not tracker.startswith("track_"):
                    raise ValueError

                token_response = await client.post(
                    "/client/passport/v1/token",
                    headers=headers,
                )
                token_response.raise_for_status()
                token_data = token_response.json()
                time_based_token = token_data["data"]
                if not isinstance(time_based_token, str) or not time_based_token:
                    raise ValueError

        except httpx.HTTPStatusError as exc:
            raise SafepayError(f"Safepay returned HTTP {exc.response.status_code}") from None
        except (httpx.TimeoutException, httpx.TransportError):
            raise SafepayError("Safepay is temporarily unavailable") from None
        except (ValueError, KeyError, TypeError):
            raise SafepayError("Safepay returned an invalid response") from None

        redirect_url = public_app_url.rstrip("/") + "/payments/return"
        cancel_url = public_app_url.rstrip("/") + "/payments/cancel"
        query = urlencode({
            "tracker": tracker,
            "tbt": time_based_token,
            "environment": self.environment,
            "source": "hosted",
            "redirect_url": redirect_url,
            "cancel_url": cancel_url,
        })
        return SafepayCheckout(
            tracker=tracker,
            checkout_url=self.checkout_base + "/checkout/pay?" + query,
        )


    async def create_checkout_url(
        self,
        *,
        tracker: str,
        public_app_url: str,
    ) -> str:
        if not isinstance(tracker, str) or not tracker.startswith("track_") or len(tracker) > 128:
            raise ValueError("tracker is invalid")
        if not public_app_url.startswith("https://"):
            raise ValueError("PUBLIC_APP_URL must use HTTPS")
        headers = {"X-SFPY-MERCHANT-SECRET": self.secret_key}
        try:
            async with httpx.AsyncClient(
                base_url=self.api_base,
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.post("/client/passport/v1/token", headers=headers)
                response.raise_for_status()
                data = response.json()["data"]
                if not isinstance(data, str) or not data:
                    raise ValueError
        except httpx.HTTPStatusError as exc:
            raise SafepayError(f"Safepay returned HTTP {exc.response.status_code}") from None
        except (httpx.TimeoutException, httpx.TransportError):
            raise SafepayError("Safepay is temporarily unavailable") from None
        except (ValueError, KeyError, TypeError):
            raise SafepayError("Safepay returned an invalid response") from None

        query = urlencode({
            "tracker": tracker,
            "tbt": data,
            "environment": self.environment,
            "source": "hosted",
            "redirect_url": public_app_url.rstrip("/") + "/payments/return",
            "cancel_url": public_app_url.rstrip("/") + "/payments/cancel",
        })
        return self.checkout_base + "/checkout/pay?" + query
