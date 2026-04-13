# Approach

I started by reading about 15 of the JSON files before writing any code. The label fragmentation jumped out immediately — almost every label is a unique string, which makes raw counting useless. The normalization problem here reminded me of entity resolution: hundreds of surface variations that map to a smaller set of real concepts. I tried auto-clustering by token overlap (Jaccard similarity), but it either merged unrelated items or missed semantic matches depending on the threshold. So I defined keyword patterns for the major categories and verified each grouping by hand.

The most useful thing I did was check who was speaking. About a third of non-safety extractions come from Voxel reps only — the pipeline treats "customer asked about X" and "Voxel demoed X" the same way. Separating those two signals changed which opportunities looked real and which were just pitch artifacts. I also used speaker attribution to refine platform-feature flagging: a customer asking for a dashboard is demand; a Voxel rep describing one is not.

I chose not to build a composite score for ranking — the category sizes are small enough that one or two misclassified items would swing a score significantly. Instead I report breadth, customer voice, and evidence depth separately and assign a confidence label. The memo makes the judgment call.

Tools: Python (pandas, matplotlib). Code is in `pipeline.py` and `ranking.py`; the notebook walks through the analysis.
