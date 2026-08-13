# utils/logical_drift.py

from sentence_transformers import SentenceTransformer, util
import numpy as np
import re

_model = SentenceTransformer("all-MiniLM-L6-v2")


# -------------------------------------------------
# 1️⃣ Block Creation
# -------------------------------------------------
def split_into_blocks(text, block_size=4):

    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    blocks = []

    for i in range(0, len(sentences), block_size):
        block = " ".join(sentences[i:i + block_size])
        if len(block.split()) > 20:
            blocks.append(block)

    return blocks


# -------------------------------------------------
# 2️⃣ Sliding Window Logical Drift
# -------------------------------------------------
def detect_logical_drift(
    full_text,
    block_size=4,
    window_size=3,
    z_threshold=1.5
):

    blocks = split_into_blocks(full_text, block_size=block_size)

    if len(blocks) < window_size * 2:
        return {
            "drift_percentage": 0.0,
            "drift_sentences": [],
            "drift_indices": []
        }

    embeddings = _model.encode(blocks)

    window_similarities = []
    window_indices = []

    # -------------------------------------------------
    # Compare neighboring sliding windows
    # -------------------------------------------------
    for i in range(len(blocks) - window_size):

        window_A = embeddings[i:i + window_size]
        window_B = embeddings[i + 1:i + 1 + window_size]

        # Average embedding per window
        window_A_mean = np.mean(window_A, axis=0)
        window_B_mean = np.mean(window_B, axis=0)

        similarity = util.cos_sim(
            window_A_mean,
            window_B_mean
        ).item()

        window_similarities.append(similarity)
        window_indices.append(i + window_size // 2)

    window_similarities = np.array(window_similarities)

    # -------------------------------------------------
    # Statistical Deviation Detection
    # -------------------------------------------------
    mean_sim = np.mean(window_similarities)
    std_sim = np.std(window_similarities)

    drift_indices = []

    for idx, sim in zip(window_indices, window_similarities):

        z_score = (mean_sim - sim) / (std_sim + 1e-6)

        if z_score > z_threshold:
            drift_indices.append(idx)

    drift_percentage = round(
        (len(drift_indices) / len(blocks)) * 100,
        2
    )

    drift_sentences = [blocks[i] for i in drift_indices]

    return {
        "drift_percentage": drift_percentage,
        "drift_sentences": drift_sentences,
        "drift_indices": drift_indices
    }