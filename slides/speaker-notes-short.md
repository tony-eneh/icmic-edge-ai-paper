# CONFROUTE: speaker notes, 20-slide deck

For `CONFROUTE_ICMIC2026_short.pptx`. **ICMIC 2026**, NTUST Taipei,
19–21 August 2026. Oral slot: **15 min presentation + 2 min Q&A + 1 min
transition.**

Same argument as the 31-slide deck, in 20 slides. Every slide carries its note
inside the PPTX, visible in Presenter View. The plan below runs to **13:10**,
which leaves room to breathe on slides 5 and 13.

The full deck keeps the backup material (full results table, confidence traces,
per-image credits). Have it open in a second window for Q&A.

---

## Timing plan

Cumulative time is the mark to hit *as you leave* the slide.

| # | Slide | Time | Cum. |
|---|-------|------|------|
| 1 | Title | 0:20 | 0:20 |
| 2 | Ships now run AI on board | 0:30 | 0:50 |
| 3 | The sea changes what the camera sees | 0:35 | 1:25 |
| 4 | Act now, ask for help, or refuse? | 0:30 | 1:55 |
| 5 | **It finds every ship, until you add haze** | 1:10 | 3:05 |
| 6 | It is not three unlucky chips | 0:50 | 3:55 |
| 7 | A confidence gate fails when you need it | 0:45 | 4:40 |
| 8 | CONFROUTE: make refusal a routing action | 0:45 | 5:25 |
| 9 | Three actions, one of them new | 0:40 | 6:05 |
| 10 | Fallback is an action, not an error code | 0:35 | 6:40 |
| 11 | Refuse only when both signals fail | 0:30 | 7:10 |
| 12 | 37,500 routing decisions | 0:35 | 7:45 |
| 13 | **Every baseline converges at about 7%** | 0:55 | 8:40 |
| 14 | Degraded links: safer and faster | 0:50 | 9:30 |
| 15 | Where we do not win | 0:40 | 10:10 |
| 16 | Both parts are load-bearing | 0:45 | 10:55 |
| 17 | **The routing layer was never the bottleneck** | 0:30 | 11:25 |
| 18 | What we are not claiming | 0:40 | 12:05 |
| 19 | Three things to take away | 0:50 | 12:55 |
| 20 | Thank you | 0:15 | 13:10 |

**Checkpoints.** Leaving slide 7 you should be at **~4:40**, leaving slide 14 at
**~9:30**. More than a minute behind at either point: drop slide 10 and slide 11
to one sentence each ("fallback means reduce speed and alert the operator, not
crash", "we refuse only when confidence *and* bandwidth both fail"), and on
slide 16 talk only to the ablation numbers.

---

## The three slides that matter

### 5. It finds every ship, until you add haze (1:10)
The centre of the talk. Real ShipsNet chips, the real adverse transform, and the
confidences the model actually produced. Same three vessels, top row and bottom
row.

Walk it: top row, all three correct, and the confidences are only 0.51 to 0.67.
The model is honestly unsure. Bottom row, the same three ships are still there,
the model now says NO SHIP on all three, at 0.96, 0.88 and 0.91.

> "It did not become uncertain. It became **more certain, and wrong.**"

Pause. Do not rush to the next slide.

### 13. Every baseline converges at about 7% (0:55)
The story is the convergence, not our line. On stable links everything that
offloads looks fine. As the link degrades all four baselines pile into
6.8–7.3%, because they all depend on an escape hatch that is no longer there.
Then point at 4.8%.

### 17. The routing layer was never the bottleneck (0:30)
Slow down. Let the slide sit for a beat before you speak. This is the sentence
you want the room to carry out of the door.

---

## The rest, briefly

- **2–3** are the operating environment in two beats: the compute is already on
  the vessel and the link is unreliable, then the input drifts and errors
  outrank latency. Slide 3 carries the inversion that separates this from
  ordinary MEC work, so land that sentence and pause.
- **4** poses the question and names the assumption in one slide. Do not defend
  the assumption, you are about to break it.
- **6** is the population view: 500 images, the lines cross. Mention that the
  three chips are 3 of 53 that behave this way, it pre-empts the cherry-picking
  question.
- **7** is the operational consequence: 39% of errors escape the gate under
  nominal conditions, 90% under adverse. This is the hinge into the method.
- **8** one point only: the router sits after scoring and before actuation, so
  it drops into an existing stack without touching the model.
- **9** say what each score prefers, then land that **guardrails override the
  scores**. The threshold controller being inspectable and certifiable matters
  to the defence and maritime people in this room.
- **10** kills the "fallback means crash" objection. Read the collision-avoidance
  row aloud and move on.
- **12** say the unsafe-rate definition out loud. "Routing-layer risk, not
  physical incidents. I want to be precise about that."
- **15** deliberate honesty. Load-only is safer under intermittent links. Say why,
  then: *"our case is the degraded regime, which is also the regime that actually
  threatens the vessel."*
- **16** ablation first (fallback carries more of the benefit than link awareness
  does), then one sentence on the chart: offload collapses from 89% to 11% and
  fallback stays a bounded minority.
- **19** read the three headers only, then stop and invite questions.

---

## Anticipated questions

The prepared answers are in [speaker-notes.md](speaker-notes.md), under
"Anticipated questions". They are unchanged: temperature scaling, synthetic
degradation, load-only under intermittent links, router overhead, threshold
transfer, the 84.8% classifier, unsafe rate as a metric, always-fall-back, and
whether the chips are cherry-picked.

The backup slides those answers lean on (full results table, confidence trace
statistics) are in `CONFROUTE_ICMIC2026.pptx`, slides 29 and 30.
