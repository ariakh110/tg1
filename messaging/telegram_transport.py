"""Bot-only MTProto transport. Fail over before sending, never after a send starts."""
import asyncio
import ipaddress
import re
import socket
from urllib.parse import parse_qs, urlsplit


class TelegramNotSent(Exception):
    """The transport knows that no sendMessage request was made."""


def parse_proxy(link):
    parsed = urlsplit(link.strip())
    if not ((parsed.scheme == "tg" and parsed.netloc == "proxy") or
            (parsed.scheme == "https" and parsed.netloc in {"t.me", "telegram.me"} and parsed.path == "/proxy")):
        raise ValueError("لینک باید tg://proxy یا https://t.me/proxy باشد.")
    query = parse_qs(parsed.query)
    try:
        host, port, secret = query["server"][0], int(query["port"][0]), query["secret"][0].lower()
    except (KeyError, ValueError, IndexError):
        raise ValueError("لینک پراکسی باید server، port و secret معتبر داشته باشد.") from None
    if not re.fullmatch(r"[a-zA-Z0-9.:-]{1,253}", host) or not 1 <= port <= 65535:
        raise ValueError("آدرس یا پورت پراکسی معتبر نیست.")
    # Telethon's MTProxy connector supports classic and randomized intermediate, not FakeTLS.
    if secret.startswith("ee") and len(secret) > 32:
        raise ValueError("پراکسی FakeTLS با secret آغازشونده با ee پشتیبانی نمی‌شود؛ لینک کلاسیک یا dd وارد کنید.")
    if len(secret) == 34 and secret.startswith("dd"):
        secret = secret[2:]
    if not re.fullmatch(r"[0-9a-f]{32}", secret):
        raise ValueError("secret باید ۳۲ رقم هگز یا پیشوند dd با ۳۲ رقم هگز باشد.")
    try:
        if not ipaddress.ip_address(host).is_global:
            raise ValueError("آدرس پراکسی باید عمومی باشد.")
    except ValueError as exc:
        if "عمومی" in str(exc):
            raise
    return host, port, secret


def validate_proxies(value):
    if not isinstance(value, list) or len(value) > 20:
        raise ValueError("حداکثر ۲۰ لینک پراکسی وارد کنید.")
    for index, link in enumerate(value):
        if not isinstance(link, str) or len(link) > 2048:
            raise ValueError(f"لینک ردیف {index + 1} معتبر نیست.")
        try:
            parse_proxy(link)
        except ValueError as exc:
            raise ValueError(f"ردیف {index + 1}: {exc}") from None
    return list(dict.fromkeys(link.strip() for link in value))


async def public_proxy(link):
    host, port, secret = parse_proxy(link)
    addresses = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError("پراکسی به آدرس عمومی اشاره نمی‌کند.")
    # Pin the resolved public IP so DNS cannot change between validation and connection.
    return addresses[0][4][0], port, "dd" + secret


async def connect_bot(cfg, link):
    from telethon import TelegramClient, connection
    from telethon.sessions import MemorySession
    proxy = await public_proxy(link)
    client = TelegramClient(MemorySession(), cfg.market_telegram_api_id, cfg.market_telegram_api_hash,
        connection=connection.ConnectionTcpMTProxyRandomizedIntermediate, proxy=proxy,
        timeout=4, connection_retries=0, request_retries=0, auto_reconnect=False,
        receive_updates=False, flood_sleep_threshold=0)
    try:
        await client.connect()
        # Explicit bot login; never prompt for a personal phone number or login code.
        await client.sign_in(bot_token=cfg.market_telegram_bot_token)
        recipient = cfg.market_telegram_channel_id
        peer = await client.get_input_entity(int(recipient) if recipient.lstrip("-").isdigit() else recipient)
        from telethon.tl.functions.channels import GetParticipantRequest
        from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator
        membership = (await client(GetParticipantRequest(peer, "me"))).participant
        if not isinstance(membership, ChannelParticipantCreator) and not (
            isinstance(membership, ChannelParticipantAdmin) and membership.admin_rights.post_messages
        ):
            raise TelegramNotSent("ربات باید مدیر کانال و دارای مجوز انتشار پست باشد.")
        return client, peer
    except BaseException:
        await client.disconnect()
        raise


def check_configuration(cfg):
    if not (cfg.market_telegram_api_id and cfg.market_telegram_api_hash and
            cfg.market_telegram_bot_token and cfg.market_telegram_channel_id and cfg.market_telegram_proxies):
        raise TelegramNotSent("توکن، مقصد، API ID، API Hash و حداقل یک پراکسی را ذخیره کنید.")


async def run_transport(cfg, text=None, index=None):
    check_configuration(cfg)
    links = cfg.market_telegram_proxies
    if index is not None:
        if not 0 <= index < len(links):
            raise TelegramNotSent("شماره پراکسی معتبر نیست.")
        links = [links[index]]
    # Bound synchronous API latency; list order determines the primary and two fallbacks.
    client = None
    for link in links[:3]:
        try:
            client, peer = await asyncio.wait_for(connect_bot(cfg, link), timeout=6)
            break
        except TelegramNotSent:
            raise
        except ImportError:
            raise TelegramNotSent("وابستگی Telethon روی سرور نصب نیست؛ نصب وابستگی‌های نسخه را تکمیل کنید.") from None
        except Exception:
            continue
    if client is None:
        raise TelegramNotSent("اتصال، ورود ربات یا دسترسی کانال از پراکسی‌های انتخاب‌شده موفق نشد؛ لینک دیگری را تست کنید و API ID/Hash و توکن را بررسی کنید.")
    try:
        if text is None:
            return {"ok": True, "detail": "اتصال، ورود ربات و مجوز انتشار کانال تأیید شد؛ پیامی ارسال نشد."}
        # No failover after this point: a timeout might follow a successful delivery.
        message = await asyncio.wait_for(client.send_message(peer, text, parse_mode=None, link_preview=False), timeout=8)
        return str(message.id)
    finally:
        await client.disconnect()


def send_mtproto(cfg, text):
    return asyncio.run(run_transport(cfg, text=text))


def test_mtproto(cfg, index):
    return asyncio.run(run_transport(cfg, index=index))
