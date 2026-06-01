from html import escape


EMPTY_EDITOR_DATA = {"blocks": []}


def normalize_editor_data(value):
    if value in (None, ""):
        return {"blocks": []}
    if not isinstance(value, dict):
        raise ValueError("ساختار محتوای ویرایشگر معتبر نیست.")
    blocks = value.get("blocks", [])
    if not isinstance(blocks, list):
        raise ValueError("فهرست بلوک‌های محتوا معتبر نیست.")
    if len(blocks) > 500:
        raise ValueError("تعداد بلوک‌های محتوا بیشتر از حد مجاز است.")
    normalized = dict(value)
    normalized["blocks"] = [block for block in blocks if isinstance(block, dict)]
    return normalized


def _render_list_items(items, tag):
    if not isinstance(items, list):
        return ""
    rendered = []
    for item in items:
        if isinstance(item, dict):
            content = item.get("content", "")
            children = _render_list_items(item.get("items", []), tag)
            rendered.append(f"<li>{content}{children}</li>")
        else:
            rendered.append(f"<li>{item}</li>")
    return f"<{tag}>{''.join(rendered)}</{tag}>" if rendered else ""


def render_editor_data(value):
    data = normalize_editor_data(value)
    rendered = []
    for block in data["blocks"]:
        block_type = block.get("type", "")
        block_data = block.get("data") if isinstance(block.get("data"), dict) else {}
        if block_type == "paragraph":
            rendered.append(f"<p>{block_data.get('text', '')}</p>")
        elif block_type == "header":
            try:
                level = min(max(int(block_data.get("level", 2)), 1), 6)
            except (TypeError, ValueError):
                level = 2
            rendered.append(f"<h{level}>{block_data.get('text', '')}</h{level}>")
        elif block_type == "list":
            tag = "ol" if block_data.get("style") == "ordered" else "ul"
            rendered.append(_render_list_items(block_data.get("items", []), tag))
        elif block_type == "quote":
            caption = block_data.get("caption", "")
            footer = f"<figcaption>{caption}</figcaption>" if caption else ""
            rendered.append(f"<blockquote><p>{block_data.get('text', '')}</p>{footer}</blockquote>")
        elif block_type == "delimiter":
            rendered.append("<hr>")
        elif block_type == "raw":
            rendered.append(str(block_data.get("html", "")))
        elif block_type == "image":
            file_data = block_data.get("file") if isinstance(block_data.get("file"), dict) else {}
            url = escape(str(file_data.get("url", "")), quote=True)
            if not url:
                continue
            caption = str(block_data.get("caption", ""))
            alt = escape(str(block_data.get("alt") or caption), quote=True)
            footer = f"<figcaption>{caption}</figcaption>" if caption else ""
            rendered.append(f'<figure><img src="{url}" alt="{alt}">{footer}</figure>')
    return "\n".join(rendered)
