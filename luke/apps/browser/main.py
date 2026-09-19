"""Luke Browser — real WebKitGTK browsing with bookmarks, history, and an
original Luke start page. On systems without the WebKit engine it degrades
to a clear install hint instead of crashing."""

import base64
import os
import sys
import time
from urllib.parse import quote

from lukeui import LukeWindow, Glyph, show_error, start
from lukepaths import state_dir
import lukeassets
import lukebrowser
import lukeapps
import gi

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk, GLib, Gdk

WEBKIT2 = None
try:
    gi.require_version("WebKit2", "4.1")
    from gi.repository import WebKit2 as _WK2
    WEBKIT2 = _WK2
except (ValueError, ImportError):
    WEBKIT2 = None

WEBKIT_MISSING_MSG = (
    "Luke Browser needs the WebKitGTK engine, which isn't installed on\n"
    "this machine yet. It ships in the Luke app bundle; ask aman or run:\n\n"
    "    sudo bash ~/.luke/apply-root.sh\n\n"
    "to install `gir1.2-webkit2-4.1` and try again.")

SEARCH = "https://duckduckgo.com/html/?q=%s"


class Browser(LukeWindow):
    def __init__(self):
        LukeWindow.__init__(self, "Luke Browser", width=980, height=660)
        if WEBKIT2 is None:
            self._missing()
            return

        self.back = self._nav("back", "Back")
        self.fwd = self._nav("max", "Forward")
        self.refresh = self._nav("refresh", "Reload")
        self.home = self._nav("home", "Home")
        self.bookmark = self._nav("star", "Bookmark")

        self.back.connect("clicked", lambda _w: self.web.go_back())
        self.fwd.connect("clicked", lambda _w: self.web.go_forward())
        self.refresh.connect("clicked", lambda _w: self.web.reload())
        self.home.connect("clicked", lambda _w: self._load_home())
        self.bookmark.connect("clicked", lambda _w: self._toggle_bookmark())

        self.entry = Gtk.Entry()
        self.entry.get_style_context().add_class("browser-entry")
        self.entry.set_placeholder_text("Search or enter an address")
        self.entry.connect("activate", self._on_go)

        go = Gtk.Button(label="Go")
        go.get_style_context().add_class("suggested-action")
        go.connect("clicked", lambda _w: self._on_go(None))

        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        bar.set_margin_start(8)
        bar.set_margin_end(8)
        bar.set_margin_top(6)
        bar.set_margin_bottom(1)
        for w in (self.back, self.fwd, self.refresh, self.home,
                  self.entry, self.bookmark, go):
            bar.pack_start(w, w is self.entry, True, 0)
        self.body.pack_start(bar, False, False, 0)

        self.bm_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.bm_bar.set_margin_start(8)
        self.bm_bar.set_margin_end(8)
        self.bm_bar.set_margin_bottom(2)
        self.body.pack_start(self.bm_bar, False, False, 0)

        self.progress = Gtk.ProgressBar()
        self.progress.set_show_text(False)
        self.progress.get_style_context().add_class("browser-progress")
        self.body.pack_start(self.progress, False, False, 0)

        self.web = WEBKIT2.WebView()
        self.web.set_hexpand(True)
        self.web.set_vexpand(True)
        ctx = self.web.get_context()
        ctx.register_uri_scheme("luke", self._scheme)
        self.web.connect("load-changed", self._on_load)
        self.web.connect("notify::estimated-load-progress", self._on_progress)
        self.web.connect("notify::uri", self._on_uri)
        self.body.pack_start(self.web, True, True, 0)

        self._load_home()

    # ---- helpers ----------------------------------------------------------
    def _nav(self, glyph, tip):
        b = Gtk.Button()
        b.add(Glyph(glyph, size=18))
        b.set_tooltip_text(tip)
        b.get_style_context().add_class("flat")
        return b

    def _missing(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_start(48)
        box.set_margin_end(48)
        box.set_margin_top(56)
        box.set_margin_bottom(56)
        t = Gtk.Label(label="WebKit engine required")
        t.get_style_context().add_class("luke-title")
        m = Gtk.Label(label=WEBKIT_MISSING_MSG, wrap=True)
        m.get_style_context().add_class("luke-sub")
        box.pack_start(t, False, False, 0)
        box.pack_start(m, False, False, 0)
        self.body.pack_start(box, True, True, 0)
        self.show_all()

    # ---- behaviour --------------------------------------------------------
    def _on_go(self, _w):
        self.web.load_uri(self._address(self.entry.get_text().strip()))

    def _address(self, raw):
        if not raw:
            return _HOME
        if "://" in raw or raw.startswith(("about:", "file:")):
            return raw
        if " " not in raw and "." in raw and raw.endswith(
                ("com", "org", "net", "io", "dev", "lu", "xyz")):
            return "https://%s" % raw
        return SEARCH % quote(raw)

    def _load_home(self):
        self.web.load_html(_home_html(), "luke://home")

    def _scheme(self, request, _userdata):
        uri = request.get_uri()
        if uri.startswith("luke://go/"):
            q = uri.split("luke://go/", 1)[1]
            self.web.load_uri(SEARCH % quote(q))
        elif uri.startswith("luke://app/"):
            app_id = uri.split("luke://app/", 1)[1]
            app = lukeapps.get_app(app_id)
            if app is not None:
                lukeapps.launch(app)
                self.hide()

    def _toggle_bookmark(self):
        uri = self.web.get_uri() or ""
        if not uri or uri.startswith("luke://"):
            return
        title = self.web.get_title() or uri
        if lukebrowser.visited(uri):
            lukebrowser.remove_bookmark(uri)
        else:
            lukebrowser.add_bookmark(title, uri)
        self._refresh_bookmarks()

    def _refresh_bookmarks(self):
        for child in self.bm_bar.get_children():
            self.bm_bar.remove(child)
        for bm in lukebrowser.bookmarks()[:10]:
            b = Gtk.Button(label=bm["title"][:22] or "…")
            b.get_style_context().add_class("luke-chip")
            b.set_tooltip_text(bm["url"])
            b.connect("clicked", lambda _w, u=bm["url"]: self.web.load_uri(u))
            self.bm_bar.pack_start(b, False, False, 0)
        self.bm_bar.show_all()

    # ---- webview events ---------------------------------------------------
    def _on_load(self, _w, event):
        if event == _WK2.LoadEvent.FINISHED:
            self.progress.set_visible(False)

    def _on_progress(self, _w, _pspec):
        self.progress.set_fraction(self.web.get_estimated_load_progress())

    def _on_uri(self, _w, _pspec):
        uri = self.web.get_uri() or ""
        if uri.startswith("luke://"):
            self.entry.set_text("")
            return
        self.entry.set_text(uri)
        if uri.startswith("http"):
            lukebrowser.record(self.web.get_title() or uri, uri)
        self._refresh_bookmarks()


_HOME = "luke://home"


def _home_html():
    mark = lukeassets.brand_mark()
    mark64 = ""
    if mark:
        try:
            with open(mark, "rb") as fh:
                mark64 = base64.b64encode(fh.read()).decode()
        except OSError:
            pass

    web = lukeapps.apps(category="Web")
    if not web:
        web = lukeapps.apps()[:8]
    tiles = ""
    for app in web[:8]:
        tiles += ("<div class='tj' onclick=\"location='luke://app/%s'\">"
                  "<span class='ct' style='background:%s'>%s</span>"
                  "<b>%s</b></div>"
                  % (app.id, app.color or "#255", app.name[0], app.name))

    return _HOME_HTML % (mark64, tiles)


_HOME_HTML = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Luke Home</title><style>
*{box-sizing:border-box}body{margin:0;min-height:100vh;color:#EAF1F8;
font-family:'Noto Sans',sans-serif;background:
radial-gradient(1200px 700px at 85% -10%, #123a3f 0%, transparent 60%),
radial-gradient(900px 600px at -5% 110%, #1d2b52 0%, transparent 55%),#0A0F17;
display:flex;align-items:center;justify-content:center;height:100vh}
.wrap{text-align:center;padding:24px}
.mark{width:88px;height:88px;margin:0 auto 18px;border-radius:22px}
.mark img{width:100%;height:100%}
.word{font-size:44px;font-weight:800;letter-spacing:10px;text-indent:10px;
margin:0;color:#EAF1F8} .word span{color:#33E0B0}
.tag{color:#6C7B92;margin:2px 0 26px;font-size:13px}
.bar{display:flex;justify-content:center;margin-bottom:34px}
form{display:flex;width:460px;max-width:92vw}
input{flex:1;background:#111A29;border:1px solid #26344B;border-left:none;
color:#EAF1F8;padding:13px 16px;font-size:14px;outline:none}
.searchglyph{width:44px;background:#111A29;border:1px solid #26344B;
border-right:none;display:flex;align-items:center;justify-content:center}
button{background:#33E0B0;border:none;color:#04302A;font-weight:700;
padding:0 22px;border-radius:0 12px 12px 0;font-size:14px;cursor:pointer}
.gear{display:inline-block;width:24px;height:24px;border-radius:60% 60% 6px 6px;
background:linear-gradient(#33E0B0,#159E7E);margin:14px 0}
.tiles{display:flex;flex-wrap:wrap;justify-content:center;gap:14px;max-width:760px}
.tj{width:104px;padding:14px 6px;border-radius:16px;background:#0E1420;
border:1px solid #1D2839;color:#EAF1F8;cursor:pointer}
.tj:hover{background:#131B28;border-color:#33E0B0}
.ct{display:flex;width:52px;height:52px;border-radius:14px;margin:0 auto 10px;
color:#fff;font-size:26px;font-weight:700;align-items:center;justify-content:center}
.tj b{font-size:12px;font-weight:600;color:#EAF1F8}
</style></head><body>
<div class="wrap">
  <div class="mark">%s</div>
  <h1 class="word">LUK<span>E</span></h1>
  <p class="tag">WHERE OUR IDEAS MEET THE OPEN WEB</p>
  <div class="bar">
    <form action="#" onsubmit="return false">
      <span class="searchglyph"><span class="gear"></span></span>
      <input id="q" placeholder="Search the web…" autofocus>
      <button type="submit" onclick="luke_go()">Go</button>
    </form>
  </div>
  <div class="tiles">%s</div>
</div>
<script>
function luke_go(){var v=document.getElementById('q').value;if(v)
document.location='luke://go/'+encodeURIComponent(v)}
var q=document.getElementById('q');
q.addEventListener('keydown',function(e){if(e.key==='Enter')luke_go()});
</script>
</body></html>"""


if __name__ == "__main__":
    start(Browser)