# OTBM Item Remapper

![Platform](https://img.shields.io/badge/platform-Windows-blue)
![Version](https://img.shields.io/badge/release-v1.0.0-green)
![Python](https://img.shields.io/badge/python-stdlib%20only-3776AB)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

Convert a Tibia `.otbm` map's **item IDs** from one server's item table to
another — for example, porting an old **0.4 / classic 8.60** map onto a modern
**TFS 1.8 / 8.60** distro, or onto a **Canary / OTServBR-Global** fork. Items are
matched so they keep the **same in-game appearance**; only the server-side ID that
each tile references is rewritten to the value the target server expects.

![OTBM Item Remapper screenshot](screenshot.png)

---

## Why you need this

A `.otbm` map doesn't store sprites — every item on it is just a **server item
ID** (the number from `items.otb` / `items.xml`). Those IDs are assigned
per-distro and almost never line up between two servers. Drop a map authored on
server **A** straight into server **B** and you get the classic result: walls turn
into ladders, grass turns into fire fields, and half your decoration becomes
"unknown item."

This tool rebuilds the map's item IDs against the target server's table so the map
looks **identical** on the new server, leaving the geometry, spawns, houses, and
client version untouched.

## Features

- **Two target formats**
  - **Classic `items.otb`** (TFS, OTX, and most 8.x–10.x distros) — matched by
    shared **clientID**, the stable anchor both tables agree on.
  - **Canary `appearances.dat`** (Canary / OTServBR-Global and other modern forks
    that dropped `items.otb`) — matched by **item name**.
- **Custom-item relocation** — items that exist only on the source are moved to
  fresh free IDs in the new `items.otb`, with optional `items.xml` definitions
  generated for them.
- **Fail-safe atomic outputs** — nothing is written unless the *entire* conversion
  succeeds, so a failure can never leave you with a half-rewritten map.
- **Hardened OTBM parser** — models the real TFS tile layout (including the `ZONE`
  zone-id list) and **stops loudly** on any tile attribute it doesn't recognise
  rather than silently corrupting your map.
- **Detailed report** — every conversion emits `remap-report.md` and a full
  old→new `remap.json` so you can audit exactly what changed.
- **No install, no Python** — a single ~12 MB Windows `.exe`. Pure Python standard
  library under the hood (tkinter GUI), so the executable has zero runtime
  dependencies.

---

## Download

**[⬇ Download the latest `.exe` from Releases](../../releases/latest)** — one
Windows executable. No install, no Python required. Just double-click it.

Prefer to build it yourself? See [Building from source](#building-from-source).

---

## Quick start

1. Launch **`OTBM Item Remapper.exe`**.
2. At the top, choose your **Target** format:
   **`items.otb (classic)`** or **`Canary appearances.dat`**.
3. Fill in the file pickers for that mode (below).
4. Click **Convert** and watch the log. On success you'll get a
   `<MapName>.remapped.otbm` plus a report in your output folder.
5. Rename the output to your map's name and drop it into the new server's
   `data/world/`.

---

## Mode 1 — Classic (`items.otb` → `items.otb`)

Use this when the target server still uses an `items.otb` table (TFS 0.x–1.x, OTX,
and most 8.x–10.x distros).

**Inputs**

| Field | What to provide |
| --- | --- |
| **Map (.otbm)** | The map you want to convert. |
| **Source items.otb (old)** | The item table the map was authored against — from the *old* server's `data/items/`. |
| **Target items.otb (new)** | The item table to convert **to** — your *new* distro's `data/items/`. |
| **Source items.xml (optional)** | Only needed to auto-generate definitions for genuinely custom items. Leave empty if you don't have customs. |
| **Output folder** | Where results are written (defaults to a `converted/` folder next to the map). |

**Outputs**

- **`<MapName>.remapped.otbm`** — the converted map. Rename it to your map name and
  put it in the server's `data/world/`.
- **`items.otb`** — the target table, plus any relocated custom items. With **zero**
  customs this is byte-for-byte your target `items.otb`, so you can just keep using
  your own.
- **`items.custom.xml`** — server-side definitions for relocated custom items (only
  produced if customs were found **and** a source `items.xml` was supplied).
- **`remap-report.md`** — human-readable summary of what matched, what was
  relocated, and what couldn't be anchored.
- **`remap.json`** — the complete old→new ID map, for scripting or auditing.

---

## Mode 2 — Canary (`appearances.dat`)

Canary, OTServBR-Global, and other modern forks dropped `items.otb` entirely —
item appearances now live in **`appearances.dat`** (a protobuf file), and names
live in `items.xml`. There is no shared clientID to anchor on across that
boundary, so this mode matches items **by name** instead.

**Inputs**

| Field | What to provide |
| --- | --- |
| **Map (.otbm)** | The map you want to convert. |
| **Source items.xml (old)** | Your *old* server's `items.xml` — this supplies the item **names** to match on. |
| **Target appearances.dat (Canary)** | From the *new* Canary server's `data/items/`. |
| **Same-era source: match by ID first** *(checkbox)* | Tick this only when the source map is **already** from an appearances-era server (another Canary/OTServBR fork). See below. |
| **Output folder** | Where results are written. |

**Same-era fast path.** If your source is already a Canary/12+ map, ticking
**"match by ID first"** keeps every item ID that already exists in the target
Canary as-is (fast and exact), and only falls back to name-matching for the rest.
This makes 12+ → Canary conversions come out near-identical instead of being
needlessly re-matched by name.

**Outputs**

- **`<MapName>.remapped.otbm`** — the converted map.
- **`remap-report.md`** — lists every item bucketed as **exact**, **ambiguous**
  (auto-resolved to the lowest matching ID), **id-matched** (same-era fast path), or
  **unmatched**.
- **`remap.json`** — the complete old→new ID map.

> **Cross-era conversions are best-effort, not a perfect port.** Old → new
> (8.6 / 10.x → Canary) reorganised names and sprites, so expect a meaningful
> *unmatched* tail to clean up in a map editor. Same-era maps (12+ → Canary) match
> near-perfectly. **Unmatched items are never dropped** — they keep their original
> IDs and are listed in the report so you can fix the tail by hand.

---

## Reading the report

`remap-report.md` groups every item ID the map uses into buckets:

**Classic mode**

| Bucket | Meaning |
| --- | --- |
| **matches** | Anchored 1:1 by clientID to a target item. |
| **customs** | Existed only on the source; relocated to a fresh free ID in the new `items.otb`. |
| **ambiguous** | Multiple target items shared the clientID; auto-resolved to the lowest ID. |
| **unanchored** | No clientID match in the target; left with its original ID (review these). |
| **changed** | How many IDs actually differ between old and new. |

**Canary mode**

| Bucket | Meaning |
| --- | --- |
| **id_matched** | (Same-era fast path) ID already existed in the target Canary; kept as-is. |
| **exact** | Matched 1:1 by name. |
| **ambiguous** | Several Canary items shared the name; auto-resolved to the lowest ID. |
| **unmatched** | No name match; left with its original ID (fix in a map editor). |
| **changed** | How many IDs actually differ. |

---

## How it works

**Classic (clientID anchoring).** Both `items.otb` files describe the *same* 8.60
client item set, so each item carries a **clientID** that means the same thing in
either table. For every item ID the map uses, the tool reads its clientID in the
**source** table, then finds which **server ID** the **target** table assigns to
that same clientID — and rewrites the map to use it. Items whose clientID has no
counterpart in the target are relocated to fresh free IDs.

**Canary (name bridge).** Across the `items.otb` → `appearances.dat` boundary
clientIDs and sprite IDs don't survive, but **names** mostly do. The tool reads
each source item's name from `items.xml` and matches it against the names in the
target `appearances.dat`, with an optional ID-first fast path for same-era sources.

The map's geometry and its `-spawn.xml` / `-house.xml` companions carry over
**unchanged** — they store names and positions, not item IDs.

## Safety guarantees

- **Atomic writes.** Outputs are staged in a temp directory and only moved into
  place if the whole conversion succeeds. A failure leaves your inputs and output
  folder untouched — never a half-broken map.
- **Client version is preserved.** The OTBM client-version field is left exactly as
  it was; rewriting it makes the engine reject the map.
- **Fail-loud parsing.** Any tile attribute the parser doesn't explicitly model
  makes it stop and report, rather than guess and corrupt.

## Known limitations

- **OTBM maps only.**
- The parser models the tile attributes the TFS engine defines (`TILE_FLAGS`
  including the `ZONE` zone-id list, and inline ground items). Hit a map with some
  other/unknown tile attribute and the tool **stops and tells you** — open an issue
  with the map so coverage can be extended.
- Cross-era Canary conversions (see Mode 2) are best-effort by nature; budget time
  to clean up the unmatched tail in a map editor.

## Building from source

```powershell
pip install pyinstaller
./build.ps1
```

Produces `dist\OTBM Item Remapper.exe`. The source is pure Python standard library
(tkinter GUI), so the executable has no external runtime dependencies.

To run straight from source instead:

```powershell
python src\gui.py
```

## License

[MIT](LICENSE) © mcbisken
