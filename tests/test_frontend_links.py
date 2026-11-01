import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit


ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    "home": "index.html",
    "login": "pages/auth/login.html",
    "register": "pages/auth/register.html",
    "reset-password": "pages/auth/reset-password.html",
    "profile": "pages/profile/profile.html",
    "admin": "pages/admin/admin.html",
}
SITE_ROOT = "https://maxfell310.github.io/u-invest/"


class HtmlReferences(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = []
        self.ids = set()
        self.site_links = set()
        self.site_root = None

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if attributes.get("id"):
            self.ids.add(attributes["id"])
        if attributes.get("data-site-link"):
            self.site_links.add(attributes["data-site-link"])
        if tag == "meta" and attributes.get("name") == "u-invest-site-root":
            self.site_root = attributes.get("content")
        for attribute in ("href", "src", "poster"):
            if attributes.get(attribute):
                self.references.append((attribute, attributes[attribute]))
        for value in attributes.get("srcset", "").split(","):
            source = value.strip().split(" ", 1)[0]
            if source:
                self.references.append(("src", source))


def _read_html(path):
    parser = HtmlReferences()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def _local_path(url):
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc:
        return None
    return parsed.path


def test_html_links_and_static_resources_exist():
    html_files = sorted(
        path
        for path in ROOT.rglob("*.html")
        if not any(part.startswith(".") for part in path.relative_to(ROOT).parts)
    )
    assert html_files, "No HTML pages found"

    errors = []
    for page in html_files:
        parser = _read_html(page)
        page_url = urljoin(SITE_ROOT, page.relative_to(ROOT).as_posix())
        if parser.site_root:
            resolved_root = urljoin(page_url, parser.site_root)
            assert resolved_root == SITE_ROOT, (
                f"{page.relative_to(ROOT)} resolves site root to {resolved_root}"
            )
        else:
            assert page == ROOT / "assets/components/header.html", (
                f"{page.relative_to(ROOT)} has no site-root meta"
            )

        for kind, reference in parser.references:
            path = _local_path(reference)
            if path is None:
                continue
            target_url = urljoin(page_url, reference)
            target_path = _local_path(urlsplit(target_url).path)
            if target_path is None or not target_url.startswith(SITE_ROOT):
                errors.append(f"{page.relative_to(ROOT)}: escapes /u-invest/: {reference}")
                continue
            target = ROOT / Path(target_path.removeprefix("/u-invest/"))
            if not target.is_file():
                errors.append(
                    f"{page.relative_to(ROOT)}: missing {kind} {reference}"
                )
                continue
            fragment = urlsplit(reference).fragment
            if fragment and target.suffix == ".html":
                target_parser = _read_html(target)
                if fragment not in target_parser.ids:
                    errors.append(
                        f"{page.relative_to(ROOT)}: missing anchor {reference}"
                    )

    assert not errors, "Broken local links/resources:\n" + "\n".join(errors)


def test_header_component_and_favicon_exist():
    assert (ROOT / "assets/components/header.html").is_file()
    assert (ROOT / "logo/logo.jpg").is_file()
    for page in (ROOT / route for route in PAGES.values()):
        parser = _read_html(page)
        favicon = [
            value
            for kind, value in parser.references
            if kind == "href" and value.endswith("logo/logo.jpg")
        ]
        assert favicon, f"{page.relative_to(ROOT)} does not reference logo.jpg"


def test_central_header_routes_match_published_pages():
    source = (ROOT / "assets/js/shared/api-config.js").read_text(encoding="utf-8")
    route_block = re.search(
        r"const routes = Object\.freeze\(\{(.*?)\n  \}\);", source, re.S
    )
    assert route_block, "Could not find centralized route map"
    routes = dict(
        re.findall(r'^\s*(\w+): "([^"]+)"', route_block.group(1), re.M)
    )

    expected = {
        "home": "index.html",
        "login": PAGES["login"],
        "register": PAGES["register"],
        "resetPassword": PAGES["reset-password"],
        "profile": PAGES["profile"],
        "admin": PAGES["admin"],
        "portfolio": PAGES["profile"] + "#portfolio",
    }
    for name, route in expected.items():
        assert routes.get(name) == route, (
            f"Header route {name!r} should be {route!r}, got {routes.get(name)!r}"
        )
    header = (ROOT / "assets/components/header.html").read_text(encoding="utf-8")
    header_links = set(re.findall(r'data-site-link="([^"]+)"', header))
    assert header_links <= routes.keys(), (
        f"Header links without centralized routes: {header_links - routes.keys()}"
    )
    assert {"home", "login", "register", "profile", "portfolio"} <= header_links
    assert 'data-authenticated-links hidden' in header
    assert "data-site-logout" in header
    for page in (ROOT / route for route in PAGES.values()):
        page_links = _read_html(page).site_links
        assert page_links <= routes.keys(), (
            f"{page.relative_to(ROOT)} links without centralized routes: "
            f"{page_links - routes.keys()}"
        )

    for name, route in routes.items():
        target_path, _, fragment = route.partition("#")
        target = ROOT / target_path
        assert target.is_file(), f"Header route {name!r} points to missing {target}"
        if fragment:
            assert fragment in _read_html(target).ids, (
                f"Header route {name!r} points to missing anchor #{fragment}"
            )


def test_auth_flows_use_the_shared_client_and_current_redirect_routes():
    auth_source = (ROOT / "assets/js/pages/auth.js").read_text(encoding="utf-8")
    admin_source = (ROOT / "assets/js/pages/admin.js").read_text(encoding="utf-8")
    assert "auth.signUp(" in auth_source
    assert "auth.signInWithPassword(" in auth_source
    assert "auth.resetPasswordForEmail(" in auth_source
    assert "auth.updateUser(" in auth_source
    assert "routes.login" in auth_source
    assert "routes.resetPassword" in auth_source
    assert "signInWithOtp(" in admin_source
    assert "shouldCreateUser: false" in admin_source
    assert 'window.location.href.split("#")[0]' in admin_source


def test_auth_redirects_use_current_routes_and_no_legacy_pages_remain():
    auth_source = (ROOT / "assets/js/pages/auth.js").read_text(encoding="utf-8")
    profile_source = (ROOT / "assets/js/pages/profile.js").read_text(encoding="utf-8")
    assert "routes.login" in auth_source
    assert "routes.resetPassword" in auth_source
    assert "routes.profile" in auth_source
    assert "routes.login" in profile_source
    for legacy_page in (
        "login.html",
        "register.html",
        "profile.html",
        "admin.html",
        "reset-password.html",
    ):
        assert not (ROOT / legacy_page).exists(), (
            f"Legacy root page still exists: {legacy_page}"
        )


def test_local_css_urls_exist():
    errors = []
    for stylesheet in (ROOT / "assets/css").rglob("*.css"):
        for reference in re.findall(
            r"url\(\s*[\"']?([^\"')]+)", stylesheet.read_text(encoding="utf-8")
        ):
            path = _local_path(reference)
            if path is None:
                continue
            target = (stylesheet.parent / path).resolve()
            if not target.is_file():
                errors.append(f"{stylesheet.relative_to(ROOT)}: missing {reference}")
    assert not errors, "Broken CSS resources:\n" + "\n".join(errors)
