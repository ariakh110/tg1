"""Read public catalog tables into stdout; never touches Django or a database.

Research utility, not the proposed application seed importer. No prices, images,
marketing copy, contact details or source stock claims are exported.
"""
import hashlib
import json
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


class CatalogParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.heading = ""
        self.heading_tag = None
        self.heading_parts = []
        self.tables = []
        self.table = None
        self.row = None
        self.cell = None
        self.links = []
        self.link = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("h1", "h2", "h3"):
            self.heading_tag, self.heading_parts = tag, []
        if tag == "a":
            self.link = [attrs.get("href", ""), []]
        if tag == "table":
            self.table = {"heading": self.heading, "rows": []}
        if tag == "tr" and self.table is not None:
            self.row = []
        if tag in ("th", "td") and self.row is not None:
            self.cell = []

    def handle_data(self, data):
        if self.heading_tag:
            self.heading_parts.append(data)
        if self.link is not None:
            self.link[1].append(data)
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag == self.heading_tag:
            self.heading = " ".join(" ".join(self.heading_parts).split())
            self.heading_tag = None
        if tag == "a" and self.link is not None:
            self.links.append((self.link[0], " ".join(" ".join(self.link[1]).split())))
            self.link = None
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join(" ".join(self.cell).split()))
            self.cell = None
        if tag == "tr" and self.row is not None:
            self.table["rows"].append(self.row)
            self.row = None
        if tag == "table" and self.table is not None:
            self.tables.append(self.table)
            self.table = None


def fetch(url):
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "fardafoolad.com":
        raise ValueError("Only the specified public source is allowed")
    request = Request(url, headers={"User-Agent": "KavehMetal-CatalogResearch/1.0"})
    with urlopen(request, timeout=30) as response:
        if urlparse(response.url).netloc != parsed.netloc:
            raise ValueError("Unexpected redirect host")
        data = response.read(5_000_001)
    if len(data) > 5_000_000:
        raise ValueError("Unexpected response size")
    parser = CatalogParser()
    parser.feed(data.decode("utf-8-sig"))
    return parser, hashlib.sha256(data).hexdigest()


def collect(url):
    parser, digest = fetch(url)
    tables = []
    for table in parser.tables:
        if not table["rows"]:
            continue
        header, *rows = table["rows"]
        if "سایز" not in header or not ({"برند", "استاندارد"} & set(header)):
            continue
        # Preserve only factual catalog columns, never the price/buy/chart cells.
        indices = {key: header.index(key) for key in ("سایز", "ضخامت", "محل بارگیری", "برند", "استاندارد", "حالت", "واحد") if key in header}
        clean_rows = []
        for row in rows:
            if len(row) != len(header):
                raise ValueError(f"Unexpected column count: {url}: {table['heading']}")
            clean_rows.append({key: row[index] for key, index in indices.items()})
        tables.append({"heading": table["heading"], "rows": clean_rows})
    return {"url": url, "html_sha256": digest, "tables": tables,
            "links": [(urljoin(url, href), label) for href, label in parser.links
                      if label and any(word in label for word in ("نبشی", "ناودانی", "سپری"))]}


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(collect(sys.argv[1]), ensure_ascii=False))
