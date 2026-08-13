import re
import os
import requests
import numpy as np
from collections import Counter
from dotenv import load_dotenv

load_dotenv()

# --------------------------------
# Sapling API Keys (Auto Switch)
# --------------------------------
SAPLING_API_KEYS = [
    key.strip()
    for key in os.getenv("SAPLING_API_KEYS", "").split(",")
    if key.strip()
]


# --------------------------------
# Sentence Split
# --------------------------------
def split_sentences(text):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if len(s.strip()) > 5]


# --------------------------------
# Chunk Creation
# --------------------------------
def create_chunks(text, size=350):
    words = text.split()
    chunks = []

    for i in range(0, len(words), size):
        chunk = " ".join(words[i:i+size])

        if len(chunk.split()) > 40:
            chunks.append(chunk)

    return chunks


# --------------------------------
# Sapling AI Detection
# --------------------------------
def sapling_ai_score(text):

    url = "https://api.sapling.ai/api/v1/aidetect"

    for key in SAPLING_API_KEYS:

        payload = {
            "key": key,
            "text": text
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            result = response.json()

            print(f"Sapling response using key {key[:6]}:", result)

            if "score" in result:
                return float(result["score"])

        except Exception as e:
            print(f"Sapling key failed {key[:6]}:", e)

    return 0.5


# --------------------------------
#  SMART AI-LIKE SENTENCE DETECTOR
# --------------------------------
def is_ai_like_sentence(sentence):

    words = sentence.lower().split()

    if len(words) < 8:
        return False

    # 1. Repetition score
    word_counts = Counter(words)
    repeated_words = sum(1 for w, c in word_counts.items() if c > 1)
    repetition_score = repeated_words / len(words)

    # 2. Unique word ratio (lexical diversity)
    unique_ratio = len(set(words)) / len(words)

    # 3. Phrase repetition (bi-grams)
    phrases = re.findall(r'\b\w+\s+\w+\b', sentence.lower())
    phrase_counts = Counter(phrases)
    repeated_phrases = sum(1 for p, c in phrase_counts.items() if c > 1)
    phrase_score = repeated_phrases / max(1, len(phrases))

    # Final heuristic decision
    if repetition_score > 0.2 or unique_ratio < 0.6 or phrase_score > 0.2:
        return True

    return False


# --------------------------------
# MAIN AI ANALYSIS
# --------------------------------
def analyze_ai_phase2(text):

    sentences = split_sentences(text)
    chunks = create_chunks(text)

    if not chunks:
        chunks = [text]

    scores = []

    # Analyze chunks (limit to 10)
    for chunk in chunks[:10]:
        score = sapling_ai_score(chunk)
        scores.append(score)

    # Average AI probability
    ai_probability = float(np.mean(scores))

    ai_percentage = round(ai_probability * 100, 2)
    human_percentage = round(100 - ai_percentage, 2)

    # --------------------------------
    #  AI Sentence Detection
    # --------------------------------
    ai_sentences = []

    for s in sentences:
        if is_ai_like_sentence(s):
            ai_sentences.append({
                "sentence": s,
                "label": "Repetitive / low-variation sentence (possible AI style)"
            })

    # --------------------------------
    # Return Results
    # --------------------------------
    return {
        "ai_percentage": ai_percentage,
        "human_percentage": human_percentage,
         "ai_sentences": ai_sentences
    }








