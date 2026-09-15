import httpx
import pytest

from app.market_data.yahoo_jp import YahooFetchError, fetch_candles


async def test_transport_error_is_normalized_to_yahoo_fetch_error(monkeypatch):
    """A raw httpx transport failure (TLS handshake error, timeout, connection
    reset, ...) must surface as YahooFetchError so call sites that only catch
    YahooFetchError (price_poll, prediction_compute) don't crash their whole
    batch on one instrument's transient network hiccup — this is exactly what
    happened with a real SSL: CERTIFICATE_VERIFY_FAILED error mid-run.
    """

    async def _raise_connect_error(self, *args, **kwargs):
        raise httpx.ConnectError("simulated TLS failure")

    monkeypatch.setattr(httpx.AsyncClient, "get", _raise_connect_error)

    with pytest.raises(YahooFetchError):
        await fetch_candles("7203.T")
