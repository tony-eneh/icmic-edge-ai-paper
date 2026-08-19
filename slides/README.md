# ICMIC 2026 talk

Slides for *CONFROUTE: Confidence-Aware Routing for Resilient Maritime Edge AI*.

**Venue:** ICMIC 2026, National Taiwan University of Science and Technology,
Taipei, 19–21 August 2026.
**Slot:** 15 min presentation, 2 min Q&A, 1 min transition.

## Files

| File | Purpose |
|------|---------|
| `CONFROUTE_ICMIC2026.pptx` | **The full deck.** 31 slides, 16:9, speaker notes embedded (Presenter View). |
| `Anthony_Uchenna_Eneh.pdf` | PDF export of the same deck, named per ICMIC guidance. Bring both on the USB stick. |
| `speaker-notes.md` | Timing plan to 14:35, per-slide notes, prepared answers for likely questions. |
| `CONFROUTE_ICMIC2026_short.pptx` | **The 20-slide version.** Same argument, same figures, fewer slides. |
| `Anthony_Uchenna_Eneh_short.pdf` | PDF export of the 20-slide version. |
| `speaker-notes-short.md` | Timing plan to 13:10 for the 20-slide version. |
| `build_pptx.py` | Builds the full PPTX. Re-run after changing figures or copy. |
| `build_pptx_short.py` | Builds the 20-slide PPTX. Self-contained, so the full deck is unaffected. |
| `make_figures.py` | Regenerates every chart into `figures/` as both PDF and 200 dpi PNG. |
| `fetch_images.py` | Downloads openly-licensed photographs from Wikimedia Commons, writes credits. |
| `image_choice.py` | Which downloaded candidate fills which slot. |
| `images/CREDITS.md` | Licence and attribution for every photograph used. |
| `slides.tex` / `slides.pdf` | Earlier LaTeX Beamer version: 23 dense slides, no photographs. Kept as an alternative. |

## Structure

### Full deck, 31 slides

One idea per slide. 27 presentation slides plus 4 backup.

- **1–5** the operating environment, one constraint per slide, full-bleed photos
- **6–7** the question, and the assumption everyone makes
- **8–12** the measurement: real ShipsNet chips, then the population, then the
  consequence for confidence-threshold offloading
- **13–17** the method: architecture, three actions, when fallback fires
- **18–23** results, including a slide on where CONFROUTE loses
- **24–27** the argument, the limitations, the takeaways
- **28–31** backup: full results, confidence traces, image credits

The talk leads with the measurement rather than the method, and closes by arguing
that calibration, not routing, is the binding constraint.

### Short deck, 20 slides

Same argument, same figures, same palette, nothing new written. All 20 are
presentation slides; there are no backup slides, so keep the full deck open in a
second window for Q&A.

- **1–4** the environment, the stakes, the question, the assumption
- **5–7** the measurement: chips, then the population, then the consequence
- **8–11** the method: architecture, three actions, what fallback means, when it fires
- **12–16** setup and results, including where CONFROUTE loses
- **17–20** the argument, the limitations, the takeaways, close

What was merged to get from 31 to 20:

| Full deck | Short deck |
|-----------|------------|
| 2–5, four scene-setting photographs | 2–3, two |
| 6–7, the question and the assumption | 4, one statement slide |
| 8–9, nominal chips then adverse chips | 5, `fig_chips` already carries both rows |
| 12, "a gate fails exactly when you need it" | title of slide 7 |
| 13, CONFROUTE section break | folded into slide 8 |
| 22–23, action mix and ablation | 16, side by side |
| 31, image credits | credits band on slide 20 |
| 28–30, backup | dropped, use the full deck |

## Rebuilding

```sh
# from the repository root, with the project venv active
python slides/make_figures.py     # charts, from the experiment CSVs
python slides/build_pptx.py       # the full deck
python slides/build_pptx_short.py # the 20-slide deck
```

To re-pick photographs:

```sh
python slides/fetch_images.py --search   # candidates + a contact sheet to review
# edit image_choice.py with the stems you want
python slides/fetch_images.py --select   # copies them in, rewrites CREDITS.md
```

To export a PDF fallback for the conference laptop, open the PPTX and *Save As*
PDF, or from PowerShell:

```powershell
$pp = New-Object -ComObject PowerPoint.Application
$pres = $pp.Presentations.Open("<abs path>\CONFROUTE_ICMIC2026.pptx", $true, $false, $false)
$pres.SaveCopyAs("<abs path>\Anthony_Uchenna_Eneh.pdf", 32)
$pres.Close(); $pp.Quit()
```

ICMIC asks for the file to be named with the presenter's full name and handed to
the session chair on a USB stick 10 minutes before the session.

## Where the numbers come from

Charts are drawn directly from `results_summary.csv`, `action_distribution.csv`
and `confidence_traces.csv` in the repository root, so re-running the experiments
and then `make_figures.py` keeps the deck in sync with the data.

The chip comparison (slides 8 and 9) reconstructs three real images from
`shipsnet.json` and applies the same `apply_adverse_maritime_condition` transform
as `experiments/run_edge_ai_routing_experiments.py`, with `SEED = 42`. The
confidences printed under each chip are the ones recorded in
`confidence_traces.csv` for those sample indices. **If the experiment seed
changes, change it in `make_figures.py` too**, or the pictures will stop matching
the numbers.

Those three chips are drawn from 53 held-out images where the classifier was
correct under nominal conditions, wrong under adverse conditions, and more
confident than before.

## Image licensing

All photographs are from Wikimedia Commons under CC BY or CC BY-SA, and every one
is attributed on the credits slide and in `images/CREDITS.md`. `fetch_images.py`
filters candidates to those licences and refuses anything below 1200 px wide.
The credits slide is generated from `images/CREDITS.json`, so attribution cannot
drift from the files actually in the deck.

Satellite imagery is from the *Ships in Satellite Imagery* (ShipsNet) dataset,
Planet Labs / Kaggle, CC BY-SA 4.0.
