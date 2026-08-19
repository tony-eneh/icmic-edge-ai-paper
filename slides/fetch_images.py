"""Fetch openly-licensed photographs from Wikimedia Commons for the ICMIC talk.

Downloads candidates for each visual theme, writes a contact sheet for review,
and records licence + attribution for every file it keeps.

    python slides/fetch_images.py --search     # gather candidates + contact sheet
    python slides/fetch_images.py --select     # keep the chosen ones, write credits
"""

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
CAND = HERE / "images" / "_candidates"
KEEP = HERE / "images"
API = "https://commons.wikimedia.org/w/api.php"
UA = "ICMIC2026-slides/1.0 (academic presentation; contact anthony@kumoh.ac.kr)"

# licences we are willing to put on a conference slide, all with attribution
OK_LICENCE = re.compile(
    r"^(CC0|CC BY(-SA)? [234]\.0|Public domain|PDM|No restrictions)", re.I)

# Curated categories beat full-text search here: Commons search surfaces scanned
# naval theses for these terms, categories surface actual photographs.
THEMES = {
    "ship_sea":   ["Category:Container ships at sea", "Category:Container ships",
                   "Category:Cargo ships at sea"],
    "ship_fog":   ["Category:Ships in fog", "Category:Fog at sea", "Category:Sea smoke"],
    "ship_storm": ["Category:Ships in heavy seas", "Category:Rough seas",
                   "Category:Storms at sea"],
    "antenna":    ["Category:Satellite communication antennas on ships",
                   "Category:Very Small Aperture Terminal",
                   "Category:Radomes on ships"],
    "bridge":     ["Category:Ship bridges"],
    "radar":      ["Category:Ship radars"],
}


def api(params):
    params = {**params, "format": "json"}
    url = f"{API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.load(r)


def strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()


def category_files(theme, categories, limit=8):
    """Photographs from the first category that yields usable, licensed files."""
    out = []
    for cat in categories:
        d = api({
            "action": "query", "generator": "categorymembers",
            "gcmtitle": cat, "gcmtype": "file", "gcmlimit": 40,
            "prop": "imageinfo", "iiprop": "url|extmetadata|size", "iiurlwidth": 1600,
        })
        for p in d.get("query", {}).get("pages", {}).values():
            ii = (p.get("imageinfo") or [{}])[0]
            em = ii.get("extmetadata", {})
            lic = strip_html(em.get("LicenseShortName", {}).get("value"))
            title = p["title"]
            if not OK_LICENCE.match(lic or ""):
                continue
            if (ii.get("width") or 0) < 1200:
                continue
            # drop scanned documents and non-photographic media
            if re.search(r"\(IA |microform|\.svg|\.tif|logo|map of", title, re.I):
                continue
            w, h = ii.get("width"), ii.get("height")
            if w and h and not (0.9 < w / h < 2.4):     # want landscape-ish
                continue
            out.append({
                "theme": theme, "title": title, "licence": lic, "category": cat,
                "artist": strip_html(em.get("Artist", {}).get("value"))[:80],
                "descurl": ii.get("descriptionurl"),
                "url": ii.get("thumburl") or ii.get("url"),
            })
            if len(out) >= limit:
                return out
        if out:
            return out
    return out


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        dest.write_bytes(r.read())


def do_search():
    CAND.mkdir(parents=True, exist_ok=True)
    manifest = []
    for theme, cats in THEMES.items():
        print(f"--- {theme}")
        for i, c in enumerate(category_files(theme, cats)):
            name = f"{theme}_{i}.jpg"
            try:
                download(c["url"], CAND / name)
                Image.open(CAND / name).verify()
            except Exception as e:                      # noqa: BLE001
                print(f"    skip {name}: {e}")
                continue
            c["file"] = name
            manifest.append(c)
            print(f"    [{i}] {c['licence']:<16} {c['title'][5:60]}")
    (CAND / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    contact_sheet(manifest)
    print(f"\n{len(manifest)} candidates -> {CAND}")


def contact_sheet(manifest, cols=6, cell=340):
    """One reviewable grid image, each cell captioned with its key."""
    rows = (len(manifest) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * (cell + 26)), "white")
    draw = ImageDraw.Draw(sheet)
    for n, m in enumerate(manifest):
        try:
            im = Image.open(CAND / m["file"]).convert("RGB")
        except Exception:                                # noqa: BLE001
            continue
        im.thumbnail((cell - 8, cell - 8))
        x, y = (n % cols) * cell, (n // cols) * (cell + 26)
        sheet.paste(im, (x + 4, y + 22))
        draw.text((x + 5, y + 6), m["file"].replace(".jpg", ""), fill="black")
    out = CAND / "contact_sheet.jpg"
    sheet.save(out, quality=88)
    print(f"contact sheet -> {out}")


def do_select(chosen):
    """chosen: {slot_name: candidate_file_stem}"""
    KEEP.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((CAND / "manifest.json").read_text(encoding="utf-8"))
    by_stem = {m["file"].replace(".jpg", ""): m for m in manifest}
    credits = []
    for slot, stem in chosen.items():
        m = by_stem[stem]
        dest = KEEP / f"{slot}.jpg"
        Image.open(CAND / m["file"]).convert("RGB").save(dest, quality=92)
        credits.append({**m, "slot": slot})
        print(f"{slot:<14} <- {stem}  ({m['licence']})")
    (KEEP / "CREDITS.json").write_text(json.dumps(credits, indent=2), encoding="utf-8")

    lines = ["# Image credits", "",
             "Photographs from Wikimedia Commons, reused under the licence shown.",
             ""]
    for c in credits:
        title = c["title"][5:]
        lines.append(f"- **{c['slot']}**: [{title}]({c['descurl']}), "
                     f"{c['artist'] or 'see source'}, {c['licence']}.")
    lines += ["", "Satellite imagery and 80x80 chips are from the *Ships in Satellite "
              "Imagery* (ShipsNet) dataset, Planet Labs / Kaggle, CC BY-SA 4.0.", ""]
    (KEEP / "CREDITS.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\ncredits -> {KEEP / 'CREDITS.md'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--search", action="store_true")
    ap.add_argument("--select", action="store_true")
    a = ap.parse_args()
    if a.search:
        do_search()
    elif a.select:
        # filled in after reviewing the contact sheet
        from image_choice import CHOSEN
        do_select(CHOSEN)
    else:
        ap.print_help()
        sys.exit(1)
