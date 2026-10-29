# U-Invest MVP Testing and Validation Report

> Complete this report only after the actual test period. Replace each prompt
> with evidence from the API summary and authorized CSV export. Do not invent
> participants, dates, findings, quotations, or outcomes. If data are
> insufficient, report that the result is inconclusive.

## 1. Research question

Which of the two U-Invest homepage headlines is associated with a higher
primary-CTA conversion rate among unique browser identifiers assigned during
the test period?

## 2. Hypothesis

- Null hypothesis (H0): the unique-visitor CTA conversion rates are equal for
  variants A and B.
- Alternative hypothesis (H1): the unique-visitor CTA conversion rates differ
  between variants A and B.
- Any directional hypothesis specified before testing: [Record it here, or
  write “None specified.”]

## 3. Experiment methodology

- Variant A: **Invest in Ukraine's Future**
- Variant B: **Discover Investment Opportunities in Ukraine**
- Assignment: the API makes a server-side 50/50 random choice for a new
  anonymous browser UUID and stores one assignment per visitor and experiment.
- Tracked events: successful page views and clicks on the primary hero CTA.
- Conversion definition:
  `(unique assigned visitors with one or more CTA clicks / unique visitors
  assigned to that variant) × 100%`.
- Visitor identification and instrumentation details:
  [Record the implementation/version used during the actual test.]
- Any protocol changes, outages, exclusions, or deviations:
  [Describe them; do not silently discard records.]

## 4. Testing period

- Start (earliest relevant timestamp): [YYYY-MM-DD, timezone]
- End (latest relevant timestamp): [YYYY-MM-DD, timezone]
- Source used to establish the dates: [API summary/export/other]
- Collection interruptions or changes: [Describe, or “None recorded.”]

## 5. Participant count

| Measure | Observed count |
|---|---:|
| Unique browser identifiers assigned to A | [ ] |
| Unique browser identifiers assigned to B | [ ] |
| Total assigned identifiers | [ ] |
| Feedback submissions | [ ] |

These are browser identifiers, not verified people. Describe any known
recruitment or sample-selection limitations: [Complete from actual testing.]

## 6. Quantitative results

| Variant | Assigned visitors | Page-view events | Unique CTA converters | Total CTA clicks | Conversion rate |
|---|---:|---:|---:|---:|---:|
| A | [ ] | [ ] | [ ] | [ ] | [ ]% |
| B | [ ] | [ ] | [ ] | [ ] | [ ]% |

Conversion-rate calculation or API values checked:
[Show the calculation and confirm that the denominator is assigned visitors.]

Additional observed feedback metrics:

- Average optional rating: [Value, or “No ratings submitted.”]
- Investment-interest responses (yes / maybe / no): [Counts]
- Number of submitted feedback forms: [Count]

Statistical method, if any, and result: [Specify method and assumptions, or
write “No inferential test performed.” Do not infer statistical significance
from the difference in raw percentages alone.]

## 7. Qualitative findings

Summarize themes found in actual submitted comments:

- [Theme and number of comments supporting it]
- [Theme and number of comments supporting it]

Representative anonymized quotations, if appropriate and permitted:

- [Quote and context]

Explain how comments were reviewed and how identifying details were removed:
[Complete from the actual review.]

## 8. Sustainability evaluation

Use the API's observed response distributions; each number should be supported
by submitted responses. Do not treat these opinions as evidence that any
specific product is sustainable.

| Importance response | Environmental impact | Social responsibility | Ethical business practices |
|---|---:|---:|---:|
| Not important | [ ] | [ ] | [ ] |
| Slightly important | [ ] | [ ] | [ ] |
| Moderately important | [ ] | [ ] | [ ] |
| Very important | [ ] | [ ] | [ ] |
| Unsure | [ ] | [ ] | [ ] |

Number of feedback submissions represented: [Count]

Evidence-based interpretation of these responses:
[Describe only patterns present in the collected data.]

## 9. Evidence-based conclusions

- Observed difference between variants: [Value or “Not estimable.”]
- What the collected data support: [Conclusion tied to counts and rates.]
- What the data do not support: [For example, causal or population-wide claims.]
- Overall conclusion: [Choose a supported conclusion or “Inconclusive.”]

## 10. Limitations

Discuss limitations that apply to this run, including as relevant:

- Small or self-selected sample and uncertain statistical power.
- Browser UUIDs may be cleared, duplicated across devices, or manipulated.
- Client-submitted events can be altered; bot detection is not implemented.
- Random assignment can produce unequal group sizes in a small sample.
- The test changes headline copy only and measures one primary CTA.
- Feedback is voluntary and may not represent all visitors.
- Collection outages, missing events, or protocol changes: [Document actual
  incidents.]

## 11. Recommendations

Recommendations supported by the evidence:

1. [Next step, rationale, and evidence]
2. [Next step, rationale, and evidence]

If evidence is insufficient to select a variant, recommend additional
pre-registered testing rather than declaring a winner.
