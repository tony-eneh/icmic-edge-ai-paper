# ICMIC 2026 talk

Slides for *CONFROUTE: Confidence-Aware Routing for Resilient Maritime Edge AI*.

**Venue:** ICMIC 2026, National Taiwan University of Science and Technology,
Taipei, 19–21 August 2026.
**Slot:** 15 min presentation, 2 min Q&A, 1 min transition.

## Files

| File | Purpose |
|------|---------|
| `CONFROUTE_ICMIC2026.pptx` | **The deck to present.** 31 slides, 16:9, speaker notes embedded (Presenter View). |
| `Anthony_Uchenna_Eneh.pdf` | PDF export of the same deck, named per ICMIC guidance. Bring both on the USB stick. |
| `speaker-notes.md` | Timing plan to 14:35, per-slide notes, prepared answers for likely questions. |
| `build_pptx.py` | Builds the PPTX. Re-run after changing figures or copy. |
| `make_figures.py` | Regenerates every chart into `figures/` as both PDF and 200 dpi PNG. |
| `fetch_images.py` | Downloads openly-licensed photographs from Wikimedia Commons, writes credits. |
| `image_choice.py` | Which downloaded candidate fills which slot. |
| `images/CREDITS.md` | Licence and attribution for every photograph used. |
| `slides.tex` / `slides.pdf` | Earlier LaTeX Beamer version: 23 dense slides, no photographs. Kept as an alternative. |

## Structure

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

## Rebuilding

```sh
# from the repository root, with the project venv active
python slides/make_figures.py     # charts, from the experiment CSVs
python slides/build_pptx.py       # the deck
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
