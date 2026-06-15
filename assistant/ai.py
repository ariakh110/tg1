"""سرویس هوش مصنوعیِ دستیار فروش: embedding، بازیابی دانش (RAG) و حلقهٔ گفتگو با ابزارها.

اتصال به یک نقطهٔ پایانیِ سازگار با OpenAI (base_url از تنظیمات دستیار، کلید از SiteSettings).
از urllib استفاده می‌کنیم تا وابستگی pip جدیدی لازم نباشد (هماهنگ با blog/ai.py).
"""
import json
import math
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings as dj_settings
from django.utils import timezone

from .models import AssistantKnowledge, AssistantMessage, AssistantSettings
from .tools import TOOL_SCHEMAS, execute_tool


class AssistantError(Exception):
    pass


def _timeout():
    return getattr(dj_settings, "OPENAI_API_TIMEOUT_SECONDS", 30)


def _post_json(path, body, cfg):
    api_key = cfg.api_key
    if not api_key:
        raise AssistantError("کلید OpenAI تنظیم نشده است (تنظیمات سایت → OpenAI).")
    base = (cfg.openai_base_url or "https://api.openai.com/v1").rstrip("/")
    request = Request(
        f"{base}{path}",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=_timeout()) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise AssistantError("سرویس هوش مصنوعی درخواست را نپذیرفت (کلید/مدل/اتصال را بررسی کنید).") from exc
    except (URLError, TimeoutError) as exc:
        raise AssistantError("ارتباط با سرویس هوش مصنوعی برقرار نشد.") from exc
    except json.JSONDecodeError as exc:
        raise AssistantError("پاسخ هوش مصنوعی قابل پردازش نبود.") from exc


# ---------- Embeddings / RAG ----------

def embed_texts(texts, cfg=None):
    cfg = cfg or AssistantSettings.load()
    payload = _post_json("/embeddings", {"model": cfg.embedding_model, "input": texts}, cfg)
    data = sorted(payload.get("data", []), key=lambda d: d.get("index", 0))
    return [item.get("embedding") for item in data]


def ensure_embeddings(cfg=None):
    """embed کردنِ دانش‌هایی که هنوز/دیگر embedding معتبر ندارند. تعداد به‌روزشده را برمی‌گرداند."""
    cfg = cfg or AssistantSettings.load()
    stale = [k for k in AssistantKnowledge.objects.filter(is_active=True) if k.needs_embedding]
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


def retrieve(query, cfg=None, k=None):
    """بازگرداندن متنِ دانش‌های مرتبط برای تزریق به پرامپت (RAG با fallbackِ کلیدواژه‌ای)."""
    cfg = cfg or AssistantSettings.load()
    k = k or cfg.max_context_chunks
    active = list(AssistantKnowledge.objects.filter(is_active=True))
    if not active:
        return []

    query_vec = None
    try:
        query_vec = embed_texts([query], cfg)[0]
    except AssistantError:
        query_vec = None

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
    return [entry.content_text() for entry in top]


# ---------- Chat orchestration ----------

def _build_system_prompt(cfg, knowledge_chunks):
    today = timezone.localdate().isoformat()
    knowledge_block = "\n\n---\n\n".join(knowledge_chunks) if knowledge_chunks else "(دانشی ثبت نشده است)"
    handoff = ""
    if cfg.handoff_phone:
        handoff = f"\nشمارهٔ تماس کارشناس: {cfg.handoff_phone} — {cfg.handoff_note}"
    return (
        f"نام تو: {cfg.assistant_name}\n\n"
        f"{cfg.persona}\n\n"
        f"## گردش‌کار فروش\n{cfg.sales_workflow}\n\n"
        f"## دانش فروشگاه (فقط از این‌ها و ابزارها استفاده کن)\n{knowledge_block}\n\n"
        f"## ابزارها\nبرای معرفی محصول و قیمت حتماً از ابزار جستجو/قیمت استفاده کن و قیمت را از خودت نگو."
        f"{handoff}\n"
        f"تاریخ امروز: {today}"
    )


def _history_messages(conversation, limit=10):
    msgs = list(
        conversation.messages.filter(role__in=[AssistantMessage.ROLE_USER, AssistantMessage.ROLE_ASSISTANT])
        .order_by("-created_at")[:limit]
    )
    msgs.reverse()
    return [{"role": m.role, "content": m.content} for m in msgs if m.content]


def _chat_completion(messages, cfg):
    body = {
        "model": cfg.chat_model,
        "messages": messages,
        "tools": TOOL_SCHEMAS,
        "tool_choice": "auto",
        "temperature": float(cfg.temperature),
    }
    payload = _post_json("/chat/completions", body, cfg)
    choices = payload.get("choices") or []
    if not choices:
        raise AssistantError("پاسخی از هوش مصنوعی دریافت نشد.")
    return choices[0].get("message", {})


def run_chat(conversation, user_text, cfg=None):
    """یک نوبت گفتگو: پیام کاربر را پردازش و پاسخ نهایی را برمی‌گرداند (با اجرای ابزارها)."""
    cfg = cfg or AssistantSettings.load()

    # پیام کاربر را ذخیره کن
    AssistantMessage.objects.create(conversation=conversation, role=AssistantMessage.ROLE_USER, content=user_text)

    knowledge_chunks = retrieve(user_text, cfg)
    system_prompt = _build_system_prompt(cfg, knowledge_chunks)
    history = _history_messages(conversation)
    messages = [{"role": "system", "content": system_prompt}] + history

    for _ in range(max(1, cfg.max_tool_iterations)):
        message = _chat_completion(messages, cfg)
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            reply = (message.get("content") or "").strip() or "متوجه نشدم، می‌شود واضح‌تر بفرمایید؟"
            AssistantMessage.objects.create(
                conversation=conversation, role=AssistantMessage.ROLE_ASSISTANT, content=reply
            )
            return reply

        # درخواستِ ابزار: پیام دستیار را با tool_calls برگردان و سپس نتایج را ضمیمه کن
        messages.append({"role": "assistant", "content": message.get("content") or "", "tool_calls": tool_calls})
        for call in tool_calls:
            fn = call.get("function", {})
            name = fn.get("name", "")
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            result = execute_tool(name, args, conversation, lead_capture_enabled=cfg.lead_capture_enabled)
            AssistantMessage.objects.create(
                conversation=conversation,
                role=AssistantMessage.ROLE_TOOL,
                content=name,
                tool_name=name,
                tool_payload={"args": args, "result": result},
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.get("id", ""),
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    # اگر بعد از چند دور به جمع‌بندی نرسید
    fallback = "برای ادامه، لطفاً جزئیات بیشتری بدهید یا با کارشناس تماس بگیرید."
    AssistantMessage.objects.create(conversation=conversation, role=AssistantMessage.ROLE_ASSISTANT, content=fallback)
    return fallback
