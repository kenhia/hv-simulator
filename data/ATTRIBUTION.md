# Attribution & Licensing

This dataset reuses material from the **Honorverse Wiki** (honorverse.fandom.com),
which is licensed under the **Creative Commons Attribution-ShareAlike 3.0 Unported
(CC BY-SA 3.0)** license.

- License text: https://creativecommons.org/licenses/by-sa/3.0/
- Fandom licensing notice: https://www.fandom.com/licensing

## What this means for the dataset

Because we incorporate CC BY-SA 3.0 content, any distribution of the derived data
files in this repository (or downstream products built from them) must:

1. **Attribute** the source (see per-file sources below).
2. **Share alike** — distribute derivative versions of the wiki-derived text under
   the same CC BY-SA 3.0 license (or a compatible one).
3. **Indicate changes** — we restructure prose into structured data, derive/invent
   values not present in canon, and add commentary. These modifications are noted
   in each file via the `canon` flag (`false` = our addition/derivation).

> Note: factual data points themselves (a planet's name, a star's spectral type)
> are generally not copyrightable, but the wiki's **expression** (phrasing, the
> selection/arrangement of lore text) is. The `lore`/`summary` free-text fields are
> the parts most clearly covered by CC BY-SA; treat them accordingly.

## Underlying fictional universe

The Honorverse and all associated names, places, and lore are the creative property
of **David Weber** and his publishers (Baen Books). This is a non-commercial
fan/simulation project. Canonical facts are sourced primarily from the novels and
secondarily from the Honorverse Wiki.

## Source pages used

| Date retrieved | Page | URL |
|---|---|---|
| 2026-06-13 | Star Kingdom of Manticore | https://honorverse.fandom.com/wiki/Star_Kingdom_of_Manticore |
| 2026-06-13 | Manticore System | https://honorverse.fandom.com/wiki/Manticore_System |
| 2026-06-13 | Basilisk System | https://honorverse.fandom.com/wiki/Basilisk_System |
| 2026-06-13 | Medusa | https://honorverse.fandom.com/wiki/Medusa |
| 2026-06-13 | Yeltsin's Star System | https://honorverse.fandom.com/wiki/Yeltsin's_Star_System |
| 2026-06-13 | Grayson (planet) | https://honorverse.fandom.com/wiki/Grayson_(planet) |
| 2026-06-13 | Blackbird | https://honorverse.fandom.com/wiki/Blackbird |
| 2026-06-13 | Endicott System | https://honorverse.fandom.com/wiki/Endicott_System |
| 2026-06-13 | Masada | https://honorverse.fandom.com/wiki/Masada |
| 2026-06-13 | Masada (planet) | https://honorverse.fandom.com/wiki/Masada_(planet) |
| 2026-06-13 | Raoul Courvosier II class | https://honorverse.fandom.com/wiki/Raoul_Courvosier_II_class |
| 2026-06-13 | Honor Harrington class | https://honorverse.fandom.com/wiki/Honor_Harrington_class |
| 2026-06-13 | Medusa class | https://honorverse.fandom.com/wiki/Medusa_class |
| 2026-06-13 | Star Knight class | https://honorverse.fandom.com/wiki/Star_Knight_class |
| 2026-06-13 | Reliant class | https://honorverse.fandom.com/wiki/Reliant_class |
| 2026-06-13 | Nike class | https://honorverse.fandom.com/wiki/Nike_class |
| 2026-06-13 | Edward Saganami class | https://honorverse.fandom.com/wiki/Edward_Saganami_class |
| 2026-06-13 | Invictus class | https://honorverse.fandom.com/wiki/Invictus_class |
| 2026-06-13 | Sultan class | https://honorverse.fandom.com/wiki/Sultan_class |
| 2026-06-13 | Warlord class | https://honorverse.fandom.com/wiki/Warlord_class |
| 2026-06-13 | Wormhole junction | https://honorverse.fandom.com/wiki/Wormhole_junction |
| 2026-06-13 | Wormhole terminus | https://honorverse.fandom.com/wiki/Wormhole_terminus |
| 2026-06-13 | Manticore Wormhole Junction | https://honorverse.fandom.com/wiki/Manticore_Wormhole_Junction |
| 2026-06-13 | Erewhon Wormhole Junction | https://honorverse.fandom.com/wiki/Erewhon_Wormhole_Junction |
| 2026-06-14 | Hyperspace | https://honorverse.fandom.com/wiki/Hyperspace |
| 2026-06-14 | Hyper limit | https://honorverse.fandom.com/wiki/Hyper_limit |
| 2026-06-14 | Battle of Manticore | https://honorverse.fandom.com/wiki/Battle_of_Manticore |
| 2026-06-14 | Courageous class | https://honorverse.fandom.com/wiki/Courageous_class |
| 2026-06-14 | Starhauler class | https://honorverse.fandom.com/wiki/Starhauler_class |
| 2026-06-14 | Dromedary class | https://honorverse.fandom.com/wiki/Dromedary_class |
| 2026-06-14 | Astra class | https://honorverse.fandom.com/wiki/Astra_class |
| 2026-06-14 | Atlas class (Manticore) | https://honorverse.fandom.com/wiki/Atlas_class_(Manticore) |
| 2026-06-14 | RMMS Artemis | https://honorverse.fandom.com/wiki/RMMS_Artemis |

## In-text source tag legend

Source tags used in the data files (`source` / `sources` fields) map to canon
citations as follows:

| Tag | Meaning |
|---|---|
| `HH<n>` | Honor Harrington main series, book *n* (e.g. `HH1` = *On Basilisk Station*) |
| `HH0` | *On Basilisk Station* prologue material |
| `SI<n>` | Saganami Island / *Shadow* series, book *n* |
| `CS<n>` | Crown of Slaves series, book *n* |
| `SK<n>` | Star Kingdom / *Stephanie Harrington* (treecat) YA series, book *n* |
| `HHA<n>:<story>` | Honor Harrington Anthology *n*, named story (e.g. `HHA2:WPD` = *Worlds of Honor*, "The Universe of Honor Harrington" / world data) |
| `Companion` | *The Honorverse Companion* / reference compendium |
| `UHH` | "The Universe of Honor Harrington" (David Weber essay) |
| `Jayne's Intelligence Review v1` | In-universe reference work used by the wiki for the system body chart |

These tags are transcribed from the wiki's citation templates and should be
verified against the primary novels before being treated as authoritative.
