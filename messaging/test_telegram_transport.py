import asyncio
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import AsyncMock, patch

from .telegram_transport import parse_proxy, validate_proxies, public_proxy, run_transport, TelegramNotSent

LINK = "tg://proxy?server=proxy.example.com&port=443&secret=" + "ab" * 16


class TelegramTransportTests(TestCase):
    def setUp(self):
        self.cfg = SimpleNamespace(market_telegram_api_id=123, market_telegram_api_hash="a" * 32,
            market_telegram_bot_token="secret", market_telegram_channel_id="@kavehmetal",
            market_telegram_proxies=[LINK, LINK.replace("proxy.example", "second.example")])

    def test_links_and_secret_formats(self):
        self.assertEqual(parse_proxy(LINK), ("proxy.example.com", 443, "ab" * 16))
        self.assertEqual(parse_proxy(LINK.replace("secret=", "secret=dd"))[2], "ab" * 16)
        self.assertEqual(parse_proxy(LINK.replace("tg://proxy", "https://t.me/proxy"))[0], "proxy.example.com")
        self.assertEqual(validate_proxies([LINK, LINK]), [LINK])
        for link in [LINK.replace("port=443", "port=0"), LINK.replace("secret=", "secret=ee") + "abcdef",
                     LINK.replace("proxy.example.com", "127.0.0.1"), "https://evil.example/proxy"]:
            with self.assertRaises(ValueError):
                parse_proxy(link)

    def test_dns_private_addresses_are_rejected(self):
        async def check():
            with patch.object(asyncio.get_running_loop(), "getaddrinfo", AsyncMock(return_value=[(2, 1, 6, "", ("127.0.0.1", 443))])):
                with self.assertRaises(ValueError):
                    await public_proxy(LINK)
        asyncio.run(check())

    def test_preflight_failover_and_test_does_not_send(self):
        client = SimpleNamespace(send_message=AsyncMock(), disconnect=AsyncMock())
        with patch("messaging.telegram_transport.connect_bot", AsyncMock(side_effect=[OSError(), (client, "peer")])) as connect:
            result = asyncio.run(run_transport(self.cfg))
        self.assertTrue(result["ok"])
        self.assertEqual(connect.call_count, 2)
        client.send_message.assert_not_called()
        client.disconnect.assert_awaited_once()

    def test_test_uses_only_selected_proxy(self):
        with patch("messaging.telegram_transport.connect_bot", AsyncMock(side_effect=OSError())) as connect:
            with self.assertRaises(TelegramNotSent):
                asyncio.run(run_transport(self.cfg, index=1))
        self.assertEqual(connect.call_count, 1)
        self.assertEqual(connect.call_args.args[1], self.cfg.market_telegram_proxies[1])

    def test_no_failover_after_send_timeout(self):
        client = SimpleNamespace(send_message=AsyncMock(side_effect=TimeoutError()), disconnect=AsyncMock())
        with patch("messaging.telegram_transport.connect_bot", AsyncMock(return_value=(client, "peer"))) as connect:
            with self.assertRaises(TimeoutError):
                asyncio.run(run_transport(self.cfg, text="report"))
        self.assertEqual(connect.call_count, 1)
        client.send_message.assert_awaited_once_with("peer", "report", parse_mode=None, link_preview=False)
        client.disconnect.assert_awaited_once()

    def test_missing_credentials_never_connects(self):
        self.cfg.market_telegram_api_hash = ""
        with patch("messaging.telegram_transport.connect_bot", AsyncMock()) as connect:
            with self.assertRaises(TelegramNotSent):
                asyncio.run(run_transport(self.cfg, text="report"))
        connect.assert_not_called()

    def test_missing_library_is_clear_and_never_sends(self):
        with patch("messaging.telegram_transport.connect_bot", AsyncMock(side_effect=ImportError())) as connect:
            with self.assertRaisesRegex(TelegramNotSent, "Telethon"):
                asyncio.run(run_transport(self.cfg, text="report"))
        self.assertEqual(connect.call_count, 1)
