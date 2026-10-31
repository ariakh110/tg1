"""Explicit verification transport; no automatic fallback or raw code logging."""
from .providers import safir


def ready(cfg, channel):
    return bool(cfg.is_configured if channel == 'sms' else cfg.bale_otp_enabled and cfg.safir_configured if channel == 'bale' else False)


def channels(cfg):
    return [channel for channel in ('sms', 'bale') if ready(cfg, channel)]


def send_bale_code(cfg, phone, code, request_id):
    return safir.send_otp(cfg.safir_access_key, cfg.safir_bot_id, safir.to_safir_phone(phone), code, request_id=str(request_id))
