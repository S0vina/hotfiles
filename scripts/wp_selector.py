#!/usr/bin/env python3
from logging import NullHandler

import gi
import subprocess
import argparse
import sys
import hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Gio

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")

WALLPAPER_DIR = Path.home() / ".config/mpvpaper"
CACHE_DIR = Path.home() / ".cache/wallpaper-picker/thumbs"
THUMB_SIZE = 180
SUPPORTED = {".mp4", ".mkv", ".webm", ".png", ".jpg", ".jpeg", ".gif"}

CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ── Thumbnail exibition
def cache_path(src: Path) -> Path:
    key = hashlib.sha1(str(src).encode()).hexdigest()
    return CACHE_DIR / f"{key}.png"


def make_thumb_video(src: Path, out: Path):
    subprocess.run(
        [
            "ffmpegthumbnailer",
            "-i",
            str(src),
            "-o",
            str(out),
            "-s",
            str(THUMB_SIZE),
            "-t",
            "10%",
            "-q",
            "8",
        ],
        capture_output=True,
    )


def make_thumb_image(src: Path, out: Path):
    try:
        from PIL import Image

        img = Image.open(src)
        img.thumbnail((THUMB_SIZE, THUMB_SIZE))
        img.save(out)
    except Exception:
        # fallback: just copy if PIL fails
        subprocess.run(
            [
                "convert",
                str(src),
                "-thumbnail",
                f"{THUMB_SIZE}x{THUMB_SIZE}>",
                str(out),
            ],
            capture_output=True,
        )


def ensure_thumb(src: Path) -> Path | None:
    out = cache_path(src)
    if out.exists():
        return out
    if src.suffix.lower() in {".mp4", ".mkv", ".webm"}:
        make_thumb_video(src, out)
    else:
        make_thumb_image(src, out)
    return out if out.exists() else None


def apply_wallpaper(path: Path, preview=False):
    subprocess.run(["killall", "-9", "mpvpaper"], capture_output=True)
    opts = "no-audio loop hwdec=auto panscan=1.0"
    cmd = ["mpvpaper", "-o", opts, "*", str(path)]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not preview:
        # persist last selection
        last = CACHE_DIR / "last"
        last.write_text(str(path.resolve()))
        print("deu certo")
        print(path)


class WallpaperPicker(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Wallpaper Picker")
        self.set_default_size(900, 600)

        self.wallpapers = sorted(
            p for p in WALLPAPER_DIR.rglob("*") if p.suffix.lower() in SUPPORTED
        )
        self.selected = 0
        self.preview_src = None

        self._build_ui()
        self._load_thumbs_async()
        self._connect_keys()

    def _build_ui(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(vbox)

        # Search bar
        self.search = Gtk.SearchEntry(
            placeholder_text="Filter…",
            margin_top=8,
            margin_bottom=8,
            margin_start=12,
            margin_end=12,
        )
        self.search.connect("search-changed", self._on_search)
        vbox.append(self.search)

        # Scrolled grid
        scroll = Gtk.ScrolledWindow(vexpand=True)
        vbox.append(scroll)

        self.flow = Gtk.FlowBox(
            valign=Gtk.Align.START,
            max_children_per_line=30,
            selection_mode=Gtk.SelectionMode.SINGLE,
            column_spacing=8,
            row_spacing=8,
            margin_top=8,
            margin_bottom=8,
            margin_start=12,
            margin_end=12,
        )
        self.flow.connect("child-activated", self._on_activate)
        scroll.set_child(self.flow)

        # Status bar
        self.status = Gtk.Label(
            label="Loading thumbnails…",
            margin_top=6,
            margin_bottom=6,
            css_classes=["dim-label"],
        )
        vbox.append(self.status)

        # CSS — dark overlay with selection ring
        css = Gtk.CssProvider()
        css.load_from_string("""
            window { background-color: #111; }
            .thumb-card { background: #1e1e1e; border-radius: 8px; padding: 4px; }
            .thumb-card:selected,
            flowboxchild:selected .thumb-card { outline: 3px solid #b82e3b; }
            label.name { color: #bbb; font-size: 11px; }
            .dim-label { color: #666; font-size: 11px; }
        """)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _make_card(self, wp: Path) -> Gtk.Box:
        card = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=4, css_classes=["thumb-card"]
        )
        img = Gtk.Image(pixel_size=THUMB_SIZE)
        img.set_name(str(wp))  # store path for later thumb update
        card.append(img)
        lbl = Gtk.Label(
            label=wp.name, css_classes=["name"], max_width_chars=22, ellipsize=3
        )  # 3 = END
        card.append(lbl)
        return card

    def _load_thumbs_async(self):
        self.cards = {}
        for wp in self.wallpapers:
            card = self._make_card(wp)
            self.flow.append(card)
            self.cards[str(wp)] = card

        def worker():
            with ThreadPoolExecutor(max_workers=4) as pool:
                futures = {pool.submit(ensure_thumb, wp): wp for wp in self.wallpapers}
                for f in futures:
                    wp = futures[f]
                    out = f.result()
                    if out:
                        GLib.idle_add(self._set_thumb, str(wp), out)

            GLib.idle_add(
                lambda: self.status.set_text(
                    f"{len(self.wallpapers)} wallpapers  ·  Enter to apply  ·  Esc to cancel"
                )
            )

        import threading

        threading.Thread(target=worker, daemon=True).start()

    def _set_thumb(self, wp_str: str, thumb: Path):
        card = self.cards.get(wp_str)
        if not card:
            return
        img = card.get_first_child()
        try:
            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                str(thumb), THUMB_SIZE, THUMB_SIZE, True
            )
            img.set_from_pixbuf(pb)
        except Exception:
            pass

    def _on_search(self, entry):
        q = entry.get_text().lower()

        def filter_fn(child):
            box = child.get_child()
            lbl = box.get_last_child()
            return q in lbl.get_text().lower()

        self.flow.set_filter_func(filter_fn if q else None)

    def _connect_keys(self):
        ctrl = Gtk.EventControllerKey()
        ctrl.connect("key-pressed", self._on_key)
        self.add_controller(ctrl)

    def _on_key(self, ctrl, keyval, keycode, state):
        match keyval:
            case Gdk.KEY_Escape:
                self.close()
            case Gdk.KEY_Return | Gdk.KEY_KP_Enter:
                sel = self.flow.get_selected_children()
                if sel:
                    self._activate_child(sel[0])
            case Gdk.KEY_space:
                # preview without closing
                sel = self.flow.get_selected_children()
                if sel:
                    wp = self._child_to_path(sel[0])
                    apply_wallpaper(wp, preview=True)
        return False

    def _on_activate(self, flow, child):
        self._activate_child(child)

    def _activate_child(self, child):
        wp = self._child_to_path(child)
        apply_wallpaper(wp, preview=False)

        self.close()

    def _child_to_path(self, child) -> Path:
        box = child.get_child()
        img = box.get_first_child()
        return Path(img.get_name())


class PickerApp(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id="com.yourname.wallpaper-picker",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )

    def do_activate(self):
        win = WallpaperPicker(self)
        win.present()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wallpaper Picker")
    parser.add_argument(
        "--restore",
        action="store_true",
        help="Apllies the last wallpaper set in the last section",
    )
    parser.add_argument(
        "--random",
    )

    args, gtk_args = parser.parse_known_args()
    if args.restore:
        last_wp = CACHE_DIR / "last"
        if last_wp.exists():
            wp_path = Path(last_wp.read_text().strip())
            if wp_path.exists():
                apply_wallpaper(wp_path)
                sys.exit(0)
            else:
                sys.exit(1)

    app = PickerApp()
    app.run([sys.argv[0]])
