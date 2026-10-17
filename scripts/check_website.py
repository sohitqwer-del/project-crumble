"""Check the buildless site's local links and page titles."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1] / "website" / "dist"


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids, self.titles = [], set(), 0

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if "id" in data:
            self.ids.add(data["id"])
        if tag == "title":
            self.titles += 1
        for key in ("href", "src"):
            if key in data:
                self.links.append(data[key])


def main():
    pages, problems = {}, []
    for path in ROOT.rglob("*.html"):
        page = Page()
        page.feed(path.read_text(encoding="utf-8-sig"))
        pages[path.resolve()] = page
        if page.titles != 1:
            problems.append(f"{path.name}: expected one page title")
    for path, page in pages.items():
        for link in page.links:
            url = urlsplit(link)
            if url.scheme or url.netloc:
                continue
            if not url.path:
                target = path
            else:
                target = (ROOT / unquote(url.path.lstrip("/")) if url.path.startswith("/")
                          else path.parent / unquote(url.path)).resolve()
            if target.is_dir():
                target /= "index.html"
            if not target.is_relative_to(ROOT.resolve()) or not target.is_file():
                problems.append(f"{path.name}: missing local resource {link}")
            elif url.fragment and target.suffix == ".html" and url.fragment not in pages[target].ids:
                problems.append(f"{path.name}: missing anchor {link}")
    if not pages:
        problems.append("No website pages found")
    if problems:
        raise SystemExit("\n".join(problems))
    print(f"Website: {len(pages)} HTML pages and their local links checked.")


if __name__ == "__main__":
    main()
