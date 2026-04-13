# What 99 Customer Calls Reveal About Non-Safety Demand

The extraction tells you what was *discussed* in these calls — not what was *demanded*. Across 92 usable transcripts (7 were empty), the pipeline produced 702 use cases — 471 safety, 231 non-safety. After normalizing heavily fragmented labels and separating customer voice from Voxel pitches, three non-safety opportunities stand out. Each points to a different buyer than the current EHS audience, which matters for account expansion.

## The ranking changes when you check who's talking

At face value, the top non-safety categories by call count are analytics and dashboards (33 calls), coaching and action workflows (20), and operational flow (19). But look at who's actually speaking: two-thirds of the coaching evidence comes from Voxel reps walking through existing features, not customers asking for something new. Analytics has a similar pattern — more than half its evidence is Voxel-initiated. The categories that survive a customer-voice filter look quite different from the naive ranking.

## Three signals worth acting on

**1. Operational flow and throughput** — 19 calls, Operations buyer

The broadest non-safety signal. Customers ask about conveyor congestion, pallet buildup, and dwell time. At Cobalt Ridge Fabrication, a customer in an operations meeting asked: *"Is there anything where you guys can see where boxes are starting to back up?"* These requests reuse existing zone detection and heat-map capabilities.

**2. Dock and door operations** — 12 calls, Facilities buyer

Open-door duration, trailer turnaround, and dock utilization come up in warehouse and cold-chain contexts. At Grit Stack Operations: *"We want to fire an automatic alert if all lights go out in a building and a dock door is still open."* This maps to a Facilities buyer who is not the current primary contact.

**3. Loss prevention and damage** — 10 calls, LP/Finance buyer

Fewer mentions, but the highest customer voice ratio among specific categories (63% — customers bring it up, Voxel doesn't have to pitch it). At Legacy Drive Fabrication, a customer described wanting real-time alerts when someone interacts with lockup fixtures. Every LP mention came attached to a dollar figure or liability concern — unusual in this dataset, and a sign of stronger purchase intent.

**What I left out.** Analytics and dashboards led in raw call count (33) but with only 46% customer voice — real signal exists, but not enough to rank above categories where customers are driving the conversation. Coaching had it worse at 33% customer voice, mostly Voxel demoing the Actions feature. Food safety appeared in just 3 calls, all Voxel-initiated. Integration requests (12 calls, 64% customer voice) are real demand but represent platform infrastructure, not a use-case vertical.

## How much to trust the extraction

The pipeline has high recall — it picks up most topics discussed — but three quality issues limit its usefulness for aggregation:

- **Near-zero label normalization.** 97.5% of safety labels and 98.7% of non-safety labels are unique strings. The extractor generates a fresh label per call rather than mapping to a controlled set, which makes raw counting meaningless.
- **Leaky safety/non-safety boundary.** 24 files have the exact same label in both buckets; when comparing evidence quotes, 53% of files show cross-bucket reuse. The classifier doesn't enforce a clean separation.
- **Customer need vs. Voxel demo.** 32% of non-safety items have evidence from Voxel speakers only. The pipeline doesn't distinguish between a customer raising a problem and a rep pitching a capability.

## One fix that would help most

The biggest issue is that the extractor generates free-text labels — an unbounded output space. Converting this to a classification task would fix normalization at the source: give the extractor a short menu of 15–20 predefined categories (derived from what actually appears in the data) plus an "other" slot for genuinely new concepts. This makes downstream aggregation trivial, quality monitoring straightforward, and category drift detectable. Adding a `who_raised_it` field (customer vs. Voxel rep, inferred from email domain) would address the second-biggest issue at near-zero cost.

## Caveats

I'm reading sales calls, not product usage data — what customers ask about and what they'd pay for are different questions. The dataset skews toward existing relationships (training calls, syncs), so early-funnel discovery conversations are underrepresented. And "Other" still accounts for 32 calls worth of non-safety labels that didn't fit neatly into any category; some of those may contain real signal I missed. If I had to bet: operational flow is the safest expansion play; loss prevention is the highest-ceiling one.
