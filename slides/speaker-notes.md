# CONFROUTE: speaker notes

**ICMIC 2026**, NTUST Taipei, 19–21 August 2026.
Oral slot: **15 min presentation + 2 min Q&A + 1 min transition.**

31 slides, one idea each. Most are quick beats; the weight sits on slides 7–11
(the measurement) and 18–20 (the results). Plan below runs to **14:35**.

Every slide also carries its note inside the PPTX, visible in Presenter View.

On the day: arrive 10 minutes early, bring `CONFROUTE_ICMIC2026.pptx` (and the
PDF fallback) on a USB stick, and hand it to the session chair.

---

## Timing plan

Cumulative time is the mark to hit *as you leave* the slide.

| # | Slide | Time | Cum. |
|---|-------|------|------|
| 1 | Title | 0:20 | 0:20 |
| 2 | Ships now run AI on board | 0:25 | 0:45 |
| 3 | The link is not always there | 0:25 | 1:10 |
| 4 | The sea changes what the camera sees | 0:25 | 1:35 |
| 5 | A wrong answer costs more than a slow one | 0:25 | 2:00 |
| 6 | Act, ask, or refuse? | 0:15 | 2:15 |
| 7 | Everyone assumes the model knows | 0:25 | 2:40 |
| 8 | Clear water: it finds every ship | 0:30 | 3:10 |
| 9 | **Add haze, and it stops seeing them** | 0:45 | 3:55 |
| 10 | It is not three unlucky chips | 0:40 | 4:35 |
| 11 | A confidence gate cannot see the errors | 0:40 | 5:15 |
| 12 | A gate fails exactly when you need it | 0:12 | 5:27 |
| 13 | CONFROUTE | 0:15 | 5:42 |
| 14 | One layer, model to actuator | 0:40 | 6:22 |
| 15 | Three actions, one of them new | 0:35 | 6:57 |
| 16 | Fallback is an action, not an error code | 0:35 | 7:32 |
| 17 | Refuse only when both signals fail | 0:30 | 8:02 |
| 18 | 37,500 routing decisions | 0:35 | 8:37 |
| 19 | Every baseline converges at about 7% | 0:45 | 9:22 |
| 20 | Degraded links: safer and faster | 0:40 | 10:02 |
| 21 | Where we do not win | 0:40 | 10:42 |
| 22 | The router shifts with the link | 0:30 | 11:12 |
| 23 | Both parts are load-bearing | 0:30 | 11:42 |
| 24 | The routing layer was never the bottleneck | 0:25 | 12:07 |
| 25 | What we are not claiming | 0:40 | 12:47 |
| 26 | Three things to take away | 0:40 | 13:27 |
| 27 | Thank you | 0:10 | 13:37 |

Slides 28–31 are backup (divider, full results, confidence traces, image credits).

**Checkpoints.** Leaving slide 11 you should be at **~5:15**. Leaving slide 20 at
**~10:00**. If you are more than a minute behind at either point, cut slide 16
(fallback table) and slide 23 (ablation) and say both in one sentence each.

---

## The three slides that matter

### 9. Add haze, and it stops seeing them (0:45)
The centre of the talk. These are real ShipsNet chips, the real adverse
transform, and the confidences the model actually produced. Same three vessels,
top row and bottom row.

Walk it: top row, all three correct, and note the confidences are only 0.51 to
0.67. The model is honestly unsure. Bottom row, the same three ships are still
there, the model now says NO SHIP on all three, at 0.96, 0.88 and 0.91.

> "It did not become uncertain. It became **more certain, and wrong.**"

Pause. Do not rush to the next slide.

### 19. Every baseline converges at about 7% (0:45)
The story is the convergence, not our line. On stable links everything that
offloads looks fine. As the link degrades all four baselines pile into
6.8–7.3%, because they all depend on an escape hatch that is no longer there.
Then point at 4.8%.

### 24. The routing layer was never the bottleneck (0:25)
Slow down. Let the slide sit for a beat before you speak. This is the sentence
you want the room to carry out of the door.

---

## The rest, briefly

- **2–5** are one constraint each: compute is on board, the link is unreliable,
  the input drifts, and errors outrank latency. Roughly 25 s each, keep moving.
  Slide 5 is the inversion that separates this from ordinary MEC work.
- **6–7** pose the question and name the assumption everyone makes. Do not
  defend it, you are about to break it.
- **8** exists so slide 9 lands. Same chips, clean conditions.
- **10** is the population-level version: 500 images, the lines cross.
- **11** is the operational consequence: 39% of errors escape the gate under
  nominal conditions, 90% under adverse.
- **14** one point only: the router sits after scoring and before actuation, so
  it drops into an existing stack without touching the model.
- **15** say what each score prefers, then land that **guardrails override the
  scores**. The threshold controller being inspectable and certifiable matters
  to the defence and maritime people in this room.
- **16** kills the "fallback means crash" objection. Read the collision-avoidance
  row aloud and move on.
- **18** say the unsafe-rate definition out loud. "Routing-layer risk, not
  physical incidents. I want to be precise about that."
- **21** deliberate honesty. Load-only is safer under intermittent links. Say why,
  then: *"our case is the degraded regime, which is also the regime that actually
  threatens the vessel."*
- **22** fallback stays a bounded minority. The ship keeps operating.
- **26** read the three headers only, then stop and invite questions.

---

## Anticipated questions

**"Why not just apply temperature scaling and fix the calibration?"**
Temperature scaling is a monotone transform of the logits. It can move where the
threshold should sit, but it cannot re-rank a confidently wrong prediction below
a correct one. Our failure is a *ranking* failure: 90% of adverse errors score
above the threshold. That is why we point at conformal prediction and explicit
OOD/shift detection rather than recalibration alone.

**"The degradation is synthetic. Does this hold on real imagery?"**
Fair, and it is our first stated limitation. The transform is deterministic and
physically motivated (contrast, brightness, blur, haze, sensor noise), but real
sea-state and sensor artefacts are the necessary next step, alongside real link
traces and hardware-in-the-loop.

**"Why is load-only routing safer than yours under intermittent links?"**
Because offloading still mostly works there, and offloading removes local-error
risk. Our confidence guardrail holds some tasks locally that load-only would have
shipped out. It is a real cost of the guardrail and we report it rather than
hiding it. Under degraded links that same guardrail is what wins.

**"What is the computational overhead of the router?"**
Three weighted sums and a few threshold comparisons per task. Negligible against
a ResNet-18 forward pass. That is deliberate: it runs on the same constrained
node as the model.

**"How are the thresholds chosen, and would they transfer to another vessel?"**
Offline from traces, then queue and link estimates update online without
retraining. Transfer is exactly the weakness: fixed thresholds are limitation
four, and adaptive thresholds via bandit feedback or Bayesian optimisation are
the planned fix.

**"84.8% validation accuracy is not high. Does that weaken the result?"**
It would if the claim were about accuracy. The claim is about the *relationship*
between confidence and accuracy under shift, and that relationship inverts
regardless of the operating point. A stronger classifier is a good robustness
check and we would expect the direction to hold.

**"Isn't unsafe rate a modelling artefact rather than a real safety measure?"**
Yes, and we say so on the setup slide. It measures routing-layer risk:
safety-sensitive local errors, low-confidence local decisions, failed
safety-sensitive offloads. Mapping it to physical incident probability needs
application-specific safety definitions and hardware-in-the-loop work.

**"Could the router just always fall back and look perfectly safe?"**
It could, which is why we report fallback rate and unsafe-local rate separately
and recommend the community do the same. A policy that refuses everything scores
zero unsafe outcomes and is operationally useless. Ours holds fallback to 7.6%
even in the worst regime.

**"Are those chips on slide 9 cherry-picked?"**
They are three of **53** held-out images where the model was correct under
nominal conditions, wrong under adverse conditions, *and* more confident than
before. Slide 10 gives the population view, and the backup slide has the full
trace statistics.
