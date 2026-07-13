"""سرویس هوش مصنوعیِ دستیار سئو: embedding، بازیابی دانش (RAG) و حلقهٔ گفتگو با ابزار.

اتصال به یک نقطهٔ پایانیِ سازگار با OpenAI (پیش‌فرض AvalAI؛ base_url از تنظیمات، کلید از SiteSettings).
از urllib استفاده می‌کنیم تا وابستگی pip جدیدی لازم نباشد (هماهنگ با assistant/ai.py).
"""
import json
import math
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings as dj_settings
from django.utils import timezone

from .models import SeoAssistantSettings, SeoKnowledge, SeoMessage
from .tools import TOOL_SCHEMAS, execute_tool


class SeoAssistantError(Exception):
    pass


class SeoAssistantCancelled(Exception):
    pass


def _timeout(cfg):
    configured = getattr(cfg, "request_timeout_seconds", None)
    if configured is None:
        configured = getattr(dj_settings, "SEO_ASSISTANT_API_TIMEOUT_SECONDS", 90)
    return max(30, min(110, int(configured)))


def _raise_if_cancelled(cancel_check=None):
    if cancel_check and cancel_check():
        raise SeoAssistantCancelled("درخواست توسط کاربر متوقف شد.")


def _post_json(path, body, cfg, cancel_check=None):
    _raise_if_cancelled(cancel_check)
    api_key = cfg.api_key
    if not api_key:
        raise SeoAssistantError("کلید سرویس هوش مصنوعی تنظیم نشده است (تنظیمات سایت → کلید OpenAI/AvalAI).")
    base = (cfg.openai_base_url or "https://api.avalai.ir/v1").rstrip("/")
    request = Request(
        f"{base}{path}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    timeout_seconds = _timeout(cfg)
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
        _raise_if_cancelled(cancel_check)
        return json.loads(raw)
    except HTTPError as exc:
        # خطای واقعیِ AvalAI را به ادمین نشان بده (کلید نامعتبر، مدلِ پشتیبانی‌نشده، اعتبارِ تمام‌شده و ...).
        # این دستیار فقط ادمین‌محور است، پس افشای جزئیاتِ بالادست بی‌خطر و برای دیباگ ضروری است.
        try:
            raw = exc.read().decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            raw = ""
        detail = raw[:400]
        try:
            err = json.loads(raw).get("error")
            if isinstance(err, dict) and err.get("message"):
                detail = err["message"]
        except Exception:  # noqa: BLE001 — بدنه JSON نبود؛ همان متنِ خام را نگه می‌داریم
            pass
        raise SeoAssistantError(
            f"سرویس هوش مصنوعی خطا داد (HTTP {exc.code}): {detail or 'بدون جزئیات'} "
            f"— مدلِ «{body.get('model', '?')}» / کلید / اعتبارِ AvalAI را بررسی کنید."
        ) from exc
    except (URLError, TimeoutError) as exc:
        reason = getattr(exc, "reason", None) or exc
        raise SeoAssistantError(
            f"سرویس هوش مصنوعی در مهلت {timeout_seconds} ثانیه پاسخ نداد: {reason} "
            f"(base_url: {base})."
        ) from exc
    except json.JSONDecodeError as exc:
        raise SeoAssistantError("پاسخ هوش مصنوعی قابل پردازش نبود.") from exc


# ---------- Embeddings / RAG ----------

def embed_texts(texts, cfg=None, cancel_check=None):
    cfg = cfg or SeoAssistantSettings.load()
    payload = _post_json(
        "/embeddings",
        {"model": cfg.embedding_model, "input": texts},
        cfg,
        cancel_check=cancel_check,
    )
    data = sorted(payload.get("data", []), key=lambda d: d.get("index", 0))
    return [item.get("embedding") for item in data]


def ensure_embeddings(cfg=None):
    """embed کردنِ دانش‌هایی که هنوز/دیگر embedding معتبر ندارند. تعداد به‌روزشده را برمی‌گرداند."""
    cfg = cfg or SeoAssistantSettings.load()
    stale = [k for k in SeoKnowledge.objects.filter(is_active=True) if k.needs_embedding]
    if not stale:
        return 0
    updated = 0
    for chunk_start in range(0, len(stale), 64):
        batch = stale[chunk_start:chunk_start + 64]
        vectors = embed_texts([k.content_text() for k in batch], cfg)
        for entry, vector in zip(batch, vectors):
            if not vector:
                continue
            entry.embedding = vector
            entry.embedding_model = cfg.embedding_model
            entry.embedded_hash = entry.content_hash()
            entry.embedded_at = timezone.now()
            entry.save(update_fields=["embedding", "embedding_model", "embedded_hash", "embedded_at"])
            updated += 1
    return updated


def _cosine(a, b):
    if not a or not b or len(a) != len(b):
        return -1.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return -1.0
    return dot / (na * nb)


def _keyword_score(query, text):
    terms = [t for t in query.lower().split() if len(t) > 1]
    if not terms:
        return 0
    low = text.lower()
    return sum(1 for t in terms if t in low)


def retrieve(query, cfg=None, k=None, cancel_check=None):
    """بازگرداندن متنِ دانش‌های مرتبط برای تزریق به پرامپت (RAG با fallbackِ کلیدواژه‌ای)."""
    cfg = cfg or SeoAssistantSettings.load()
    k = k or cfg.max_context_chunks
    active = list(SeoKnowledge.objects.filter(is_active=True))
    if not active:
        return []

    query_vec = None
    try:
        query_vec = embed_texts([query], cfg, cancel_check=cancel_check)[0]
    except SeoAssistantError:
        query_vec = None

    _raise_if_cancelled(cancel_check)

    scored = []
    for entry in active:
        if query_vec and entry.embedding:
            score = _cosine(query_vec, entry.embedding)
        else:
            score = _keyword_score(query, entry.content_text()) / 10.0
        scored.append((score, entry))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    top = [entry for score, entry in scored[:k] if score > 0]
    if not top:  # هیچ تطبیقی نبود؛ چند موردِ نخست را بده تا دستیار بی‌دانش نماند
        top = [entry for _s, entry in scored[:k]]
    return [f"[{entry.get_layer_display()}] {entry.content_text()}" for entry in top]


# ---------- Chat orchestration ----------

def _build_system_prompt(cfg, knowledge_chunks):
    today = timezone.localdate().isoformat()
    knowledge_block = "\n\n---\n\n".join(knowledge_chunks) if knowledge_chunks else "(دانشی ثبت نشده است؛ ابتدا ingest_seo_kb را اجرا کنید)"
    return (
        f"نام تو: {cfg.assistant_name}\n\n"
        f"{cfg.persona}\n\n"
        f"## زمینهٔ سایت هدف\n{cfg.site_context}\n\n"
        f"## دانش سئو (فقط از این‌ها و ابزار استفاده کن)\n{knowledge_block}\n\n"
        f"## ابزار\nبرای آدیت یک URL مشخص حتماً از ابزار fetch_page_seo استفاده کن و از سیگنال‌های واقعیِ صفحه نتیجه بگیر؛ "
        f"حدس نزن. اگر پاسخ در دانش بالا نبود، صادقانه بگو.\n"
        f"تاریخ امروز: {today}"
    )


def _history_messages(conversation, limit=12):
    msgs = list(
        conversation.messages.filter(role__in=[SeoMessage.ROLE_USER, SeoMessage.ROLE_ASSISTANT])
        .order_by("-created_at")[:limit]
    )
    msgs.reverse()
    return [{"role": m.role, "content": m.content} for m in msgs if m.content]


def _chat_completion(messages, cfg, cancel_check=None):
    body = {
        "model": cfg.chat_model,
        "messages": messages,
        "tools": TOOL_SCHEMAS,
        "tool_choice": "auto",
        "temperature": float(cfg.temperature),
    }
    payload = _post_json("/chat/completions", body, cfg, cancel_check=cancel_check)
    choices = payload.get("choices") or []
    if not choices:
        raise SeoAssistantError("پاسخی از هوش مصنوعی دریافت نشد.")
    return choices[0].get("message", {})


def run_chat(conversation, user_text, cfg=None, chat_request=None, cancel_check=None):
    """یک نوبت گفتگو: پیام ادمین را پردازش و پاسخ نهایی را برمی‌گرداند (با اجرای ابزار)."""
    cfg = cfg or SeoAssistantSettings.load()
    message_defaults = {"conversation": conversation, "chat_request": chat_request}

    try:
        _raise_if_cancelled(cancel_check)
        SeoMessage.objects.create(role=SeoMessage.ROLE_USER, content=user_text, **message_defaults)
        _raise_if_cancelled(cancel_check)

        knowledge_chunks = retrieve(user_text, cfg, cancel_check=cancel_check)
        _raise_if_cancelled(cancel_check)
        system_prompt = _build_system_prompt(cfg, knowledge_chunks)
        history = _history_messages(conversation)
        messages = [{"role": "system", "content": system_prompt}] + history

        for _ in range(max(1, cfg.max_tool_iterations)):
            _raise_if_cancelled(cancel_check)
            message = _chat_completion(messages, cfg, cancel_check=cancel_check)
            _raise_if_cancelled(cancel_check)
            # فقط tool_callهای معتبر؛ بعضی مدل‌ها/پراکسی‌ها (AvalAI) گاهی tool_call با name=null
            # و arguments خالی می‌فرستند — این‌ها را نادیده می‌گیریم تا نه کرش شود نه content=null ذخیره گردد.
            tool_calls = [
                c for c in (message.get("tool_calls") or [])
                if isinstance(c, dict) and ((c.get("function") or {}).get("name") or "").strip()
            ]
            if not tool_calls:
                reply = (message.get("content") or "").strip() or "متوجه نشدم، می‌شود واضح‌تر بفرمایید؟"
                _raise_if_cancelled(cancel_check)
                SeoMessage.objects.create(role=SeoMessage.ROLE_ASSISTANT, content=reply, **message_defaults)
                return reply

            messages.append({"role": "assistant", "content": message.get("content") or "", "tool_calls": tool_calls})
            for call in tool_calls:
                _raise_if_cancelled(cancel_check)
                fn = call.get("function", {})
                name = (fn.get("name") or "").strip()
                try:
                    args = json.loads(fn.get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = execute_tool(name, args, conversation)
                _raise_if_cancelled(cancel_check)
                SeoMessage.objects.create(
                    role=SeoMessage.ROLE_TOOL,
                    content=name or "tool",  # هرگز null نشود (ستون NOT NULL است)
                    tool_name=name,
                    tool_payload={"args": args, "result": result},
                    **message_defaults,
                )
                messages.append(
                    {"role": "tool", "tool_call_id": call.get("id", ""), "content": json.dumps(result, ensure_ascii=False)}
                )

        fallback = "برای جمع‌بندی دقیق‌تر، لطفاً سؤال را کمی محدودتر کنید یا URL مشخصی برای آدیت بدهید."
        _raise_if_cancelled(cancel_check)
        SeoMessage.objects.create(role=SeoMessage.ROLE_ASSISTANT, content=fallback, **message_defaults)
        return fallback
    except SeoAssistantCancelled:
        if chat_request is not None:
            chat_request.messages.all().delete()
        raise
