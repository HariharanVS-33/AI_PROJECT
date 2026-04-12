#!/usr/bin/env python3
"""
evaluate_model.py — Model Accuracy Evaluation Script
=====================================================
Run this script to evaluate the accuracy of the AI models used in the
Healthcare Lead Conversational Agent.

Evaluates:
  1. Lead Qualifier Validation Logic   (Offline — no API needed)
  2. Intent Classification Accuracy    (Gemini few-shot classifier)
  3. RAG Retrieval Relevance           (ChromaDB + Gemini embeddings)

Usage:
    python3 evaluate_model.py
"""

import os
import re
import sys
import time
import logging
from collections import defaultdict
from dotenv import load_dotenv

# ── Setup ──────────────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_ROOT)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
logging.basicConfig(level=logging.WARNING)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


# ══════════════════════════════════════════════════════════════════════════════
#  TEST DATASETS
# ══════════════════════════════════════════════════════════════════════════════

# --- Intent Classification Test Set ---
# Format: (user_message, expected_intent)
INTENT_TEST_DATA = [
    # product_query (10 samples)
    ("What IV cannulas do you manufacture?",                     "product_query"),
    ("Tell me about your blood collection tubes",                "product_query"),
    ("Do you have any respiratory care products?",               "product_query"),
    ("What are the specifications of Polycan IV cannula?",       "product_query"),
    ("Can you show me your dialysis product catalogue?",         "product_query"),
    ("What safety needles do you offer?",                        "product_query"),
    ("Tell me about your cardiology devices",                    "product_query"),
    ("What products do you have for blood management?",          "product_query"),
    ("Do you manufacture infusion sets?",                        "product_query"),
    ("List your urology products",                               "product_query"),

    # distributor_query (8 samples)
    ("How can I become a distributor?",                           "distributor_query"),
    ("I want to be a dealer for your products in Mumbai",        "distributor_query"),
    ("What is the process to become a channel partner?",         "distributor_query"),
    ("I'm interested in distributing your medical devices",      "distributor_query"),
    ("Can I get a distributorship for PolyMedicure?",            "distributor_query"),
    ("What are the requirements to become a dealer?",            "distributor_query"),
    ("I want to partner as a distributor in North India",        "distributor_query"),
    ("How do I apply for dealership?",                           "distributor_query"),

    # territory_query (6 samples)
    ("Do you have dealers in South India?",                      "territory_query"),
    ("Which states do you operate in?",                          "territory_query"),
    ("Are your products available in Kerala?",                   "territory_query"),
    ("Do you export to Middle East countries?",                  "territory_query"),
    ("What regions does PolyMedicure cover?",                    "territory_query"),
    ("Is there a distributor near Hyderabad?",                   "territory_query"),

    # pricing_query (6 samples)
    ("What is the price of your IV cannulas?",                   "pricing_query"),
    ("Can you give me a quote for 1000 blood bags?",             "pricing_query"),
    ("What are your bulk pricing options?",                      "pricing_query"),
    ("Do you offer discounts for large orders?",                 "pricing_query"),
    ("How much does the Polycan catheter cost?",                 "pricing_query"),
    ("What are the payment terms for distributors?",             "pricing_query"),

    # sales_intent (8 samples)
    ("I want to buy 500 units of IV cannulas",                   "sales_intent"),
    ("We need to place an order for medical supplies",           "sales_intent"),
    ("I'm interested in purchasing your products",               "sales_intent"),
    ("Yes, I want to proceed with the partnership",              "sales_intent"),
    ("I need to order some dialysis consumables",                "sales_intent"),
    ("We'd like to purchase blood collection tubes in bulk",     "sales_intent"),
    ("I want 200 boxes of safety needles delivered",             "sales_intent"),
    ("Please send me a purchase order form",                     "sales_intent"),

    # general_enquiry (8 samples)
    ("Hello",                                                    "general_enquiry"),
    ("What does PolyMedicure do?",                               "general_enquiry"),
    ("Tell me about your company",                               "general_enquiry"),
    ("When was PolyMedicure founded?",                           "general_enquiry"),
    ("Hi, good morning",                                         "general_enquiry"),
    ("Thank you for your help",                                  "general_enquiry"),
    ("Where is your head office located?",                       "general_enquiry"),
    ("Who is the CEO of PolyMedicure?",                          "general_enquiry"),

    # out_of_scope (8 samples)
    ("What's the weather today?",                                "out_of_scope"),
    ("Tell me a joke",                                           "out_of_scope"),
    ("Who won the cricket match?",                               "out_of_scope"),
    ("Can you help me with my homework?",                        "out_of_scope"),
    ("What's the capital of France?",                            "out_of_scope"),
    ("Write me a poem about love",                               "out_of_scope"),
    ("How to cook pasta?",                                       "out_of_scope"),
    ("Explain quantum physics",                                  "out_of_scope"),
]

# --- Lead Qualifier Validation Test Set ---
# Format: (field_key, input_value, should_be_valid)
VALIDATION_TEST_DATA = [
    # Email validation
    ("email", "john@example.com",      True),
    ("email", "user@domain.co.in",     True),
    ("email", "invalid-email",         False),
    ("email", "@no-local.com",         False),
    ("email", "no-at-sign.com",        False),
    ("email", "user@.com",             False),

    # Phone validation
    ("phone", "9876543210",            True),
    ("phone", "+91 98765 43210",       True),
    ("phone", "044-28150000",          True),
    ("phone", "123",                   False),
    ("phone", "abc",                   False),

    # Name validation
    ("first_name", "Hariharan",        True),
    ("first_name", "Li",               True),
    ("first_name", "A",                False),
    ("first_name", "123",              False),
    ("first_name", "J@ck",             False),

    # General field validation
    ("address", "123 Main Street, Chennai", True),
    ("address", "A",                   False),
    ("company_name", "Apollo Hospitals", True),
]

# --- RAG Retrieval Test Set ---
RAG_TEST_QUERIES = [
    {"query": "What IV cannulas does PolyMedicure make?",         "should_retrieve": True,  "topic": "IV cannula products"},
    {"query": "Tell me about blood collection tubes",             "should_retrieve": True,  "topic": "blood management"},
    {"query": "What dialysis products are available?",            "should_retrieve": True,  "topic": "dialysis"},
    {"query": "PolyMedicure respiratory care devices",            "should_retrieve": True,  "topic": "respiratory care"},
    {"query": "Safety needles and syringes catalogue",            "should_retrieve": True,  "topic": "safety devices"},
    {"query": "How to cook biryani?",                             "should_retrieve": False, "topic": "out of scope"},
    {"query": "Latest football scores",                           "should_retrieve": False, "topic": "out of scope"},
    {"query": "Cardiology products and accessories",              "should_retrieve": True,  "topic": "cardiology"},
    {"query": "Where is PolyMedicure headquartered?",             "should_retrieve": True,  "topic": "company info"},
    {"query": "What certifications does PolyMedicure hold?",      "should_retrieve": True,  "topic": "certifications"},
]


# ══════════════════════════════════════════════════════════════════════════════
#  UTILITY FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def print_header(title: str):
    width = 60
    print("\n" + "═" * width)
    print(f"  {title}")
    print("═" * width)


def print_subheader(title: str):
    safe_len = min(len(title), 45)
    print(f"\n  ── {title} {'─' * max(5, 50 - safe_len)}")


def colored(text: str, color: str) -> str:
    """Simple ANSI color wrapper."""
    colors = {
        "green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m",
        "cyan": "\033[96m", "bold": "\033[1m", "reset": "\033[0m",
        "dim": "\033[2m",
    }
    return f"{colors.get(color, '')}{text}{colors.get('reset', '')}"


def print_confusion_matrix(labels: list, matrix: dict):
    """Print a text-based confusion matrix."""
    short = {l: l[:7] for l in labels}
    header = "        " + " ".join(f"{short[l]:>8s}" for l in labels)
    print(f"\n{colored('  Confusion Matrix (rows=actual, cols=predicted):', 'bold')}")
    print(f"  {header}")
    for actual in labels:
        row_vals = " ".join(f"{matrix.get((actual, pred), 0):>8d}" for pred in labels)
        print(f"  {short[actual]:>7s} {row_vals}")


def compute_metrics(y_true: list, y_pred: list, labels: list) -> dict:
    """Compute accuracy, per-class precision/recall/F1, and confusion matrix."""
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    accuracy = correct / len(y_true) if y_true else 0

    tp = defaultdict(int)
    fp = defaultdict(int)
    fn = defaultdict(int)
    confusion = defaultdict(int)

    for t, p in zip(y_true, y_pred):
        confusion[(t, p)] += 1
        if t == p:
            tp[t] += 1
        else:
            fp[p] += 1
            fn[t] += 1

    per_class = {}
    for label in labels:
        prec = tp[label] / (tp[label] + fp[label]) if (tp[label] + fp[label]) > 0 else 0
        rec = tp[label] / (tp[label] + fn[label]) if (tp[label] + fn[label]) > 0 else 0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
        per_class[label] = {"precision": prec, "recall": rec, "f1": f1}

    return {
        "accuracy": accuracy,
        "correct": correct,
        "total": len(y_true),
        "per_class": per_class,
        "confusion": confusion,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  INLINE VALIDATOR (mirrors backend/core/lead_qualifier.py — no imports)
# ══════════════════════════════════════════════════════════════════════════════

def _validate_field(field_key: str, value: str) -> tuple:
    """Validate a lead form field — self-contained copy of the backend logic."""
    value = value.strip()
    if field_key == "email":
        if re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", value):
            return True, ""
        return False, "Invalid email"
    if field_key == "phone":
        digits = re.sub(r"\D", "", value)
        if len(digits) >= 7:
            return True, ""
        return False, "Invalid phone"
    if field_key in ("first_name", "last_name"):
        if len(value) >= 2 and value.replace(" ", "").isalpha():
            return True, ""
        return False, "Invalid name"
    if len(value) >= 2:
        return True, ""
    return False, "Too short"


# ══════════════════════════════════════════════════════════════════════════════
#  EVALUATION 1: LEAD QUALIFIER VALIDATION (No API needed)
# ══════════════════════════════════════════════════════════════════════════════

def evaluate_lead_qualifier():
    print_header("✅ LEAD QUALIFIER VALIDATION EVALUATION")
    print(f"  Component : Rule-based validator (regex + logic)")
    print(f"  Test Size : {len(VALIDATION_TEST_DATA)} samples")
    print()

    correct = 0
    total = len(VALIDATION_TEST_DATA)
    failures = []

    for field_key, value, expected_valid in VALIDATION_TEST_DATA:
        is_valid, _ = _validate_field(field_key, value)
        if is_valid == expected_valid:
            correct += 1
        else:
            failures.append((field_key, value, expected_valid, is_valid))

    accuracy = correct / total if total else 0

    acc_color = "green" if accuracy >= 0.90 else ("yellow" if accuracy >= 0.75 else "red")
    print(f"  {colored('Validation Accuracy', 'bold')} : {colored(f'{accuracy:.1%}', acc_color)}  "
          f"({correct}/{total} correct)")

    # Show detail table
    print()
    print(f"  {'Field':<15s} {'Input':<30s} {'Expected':<10s} {'Got':<10s} {'':>3s}")
    print(f"  {'─'*70}")
    for field_key, value, expected_valid in VALIDATION_TEST_DATA:
        is_valid, _ = _validate_field(field_key, value)
        ok = is_valid == expected_valid
        status = colored("✅", "green") if ok else colored("❌", "red")
        exp_str = "Valid" if expected_valid else "Invalid"
        got_str = "Valid" if is_valid else "Invalid"
        print(f"  {field_key:<15s} {value[:29]:<30s} {exp_str:<10s} {got_str:<10s} {status}")

    if failures:
        print_subheader(f"Failed Cases ({len(failures)})")
        for field, val, exp, got in failures:
            exp_str = colored("Valid", "green") if exp else colored("Invalid", "red")
            got_str = colored("Valid", "green") if got else colored("Invalid", "red")
            print(f"  • {field}: \"{val}\"  — Expected: {exp_str}, Got: {got_str}")

    return accuracy


# ══════════════════════════════════════════════════════════════════════════════
#  EVALUATION 2: INTENT CLASSIFICATION (API needed)
# ══════════════════════════════════════════════════════════════════════════════

def evaluate_intent_classification():
    print_header("📊 INTENT CLASSIFICATION EVALUATION")
    print(f"  Model     : Gemini 2.5 Flash (Few-Shot Prompting)")
    print(f"  Test Size : {len(INTENT_TEST_DATA)} samples")
    print(f"  Classes   : {len(set(t[1] for t in INTENT_TEST_DATA))}")
    print()

    if not GEMINI_API_KEY:
        print(f"  {colored('⚠️  GEMINI_API_KEY not set in .env — skipping API-based test', 'yellow')}")
        return None

    # Import only when API key is available
    sys.path.insert(0, PROJECT_ROOT)
    from backend.core.intent import classify

    y_true = []
    y_pred = []
    misclassified = []

    total = len(INTENT_TEST_DATA)
    for i, (message, expected) in enumerate(INTENT_TEST_DATA, 1):
        sys.stdout.write(f"\r  Testing... [{i}/{total}] ")
        sys.stdout.flush()

        predicted = classify(message)
        y_true.append(expected)
        y_pred.append(predicted)

        if predicted != expected:
            misclassified.append((message, expected, predicted))

        time.sleep(0.3)  # Rate limiting for API

    labels = sorted(set(y_true))
    metrics = compute_metrics(y_true, y_pred, labels)

    # ── Results ──
    print(f"\r  Testing... [{total}/{total}] ✅ Done!     ")
    print_subheader("Overall Results")

    acc = metrics["accuracy"]
    acc_color = "green" if acc >= 0.85 else ("yellow" if acc >= 0.70 else "red")
    print(f"\n  {colored('Accuracy', 'bold')} : {colored(f'{acc:.1%}', acc_color)}  "
          f"({metrics['correct']}/{metrics['total']} correct)")

    # ── Per-Class Table ──
    print_subheader("Per-Class Metrics")
    print(f"\n  {'Intent':<20s} {'Precision':>10s} {'Recall':>10s} {'F1-Score':>10s}")
    print(f"  {'─'*50}")

    macro_p, macro_r, macro_f1 = 0, 0, 0
    for label in labels:
        m = metrics["per_class"][label]
        p_str = f"{m['precision']:>9.1%}"
        r_str = f"{m['recall']:>9.1%}"
        f_str = f"{m['f1']:>9.1%}"
        p_color = "green" if m["precision"] >= 0.85 else ("yellow" if m["precision"] >= 0.60 else "red")
        r_color = "green" if m["recall"] >= 0.85 else ("yellow" if m["recall"] >= 0.60 else "red")
        f_color = "green" if m["f1"] >= 0.85 else ("yellow" if m["f1"] >= 0.60 else "red")
        print(f"  {label:<20s} {colored(p_str, p_color)} "
              f"{colored(r_str, r_color)} "
              f"{colored(f_str, f_color)}")
        macro_p += m["precision"]
        macro_r += m["recall"]
        macro_f1 += m["f1"]

    n = len(labels)
    print(f"  {'─'*50}")
    print(f"  {'Macro Avg':<20s} {macro_p/n:>9.1%}  {macro_r/n:>9.1%}  {macro_f1/n:>9.1%}")

    # ── Confusion Matrix ──
    print_confusion_matrix(labels, metrics["confusion"])

    # ── Misclassified ──
    if misclassified:
        print_subheader(f"Misclassified Samples ({len(misclassified)})")
        for msg, exp, pred in misclassified[:10]:
            print(f"  • \"{msg[:50]}\"")
            print(f"    Expected: {colored(exp, 'green')}  →  Got: {colored(pred, 'red')}")

    return metrics["accuracy"]


# ══════════════════════════════════════════════════════════════════════════════
#  EVALUATION 3: RAG RETRIEVAL (API needed)
# ══════════════════════════════════════════════════════════════════════════════

def evaluate_rag_retrieval():
    print_header("🔍 RAG RETRIEVAL EVALUATION")
    print(f"  Embedding  : Gemini (gemini-embedding-001)")
    print(f"  Vector DB  : ChromaDB")
    print(f"  Test Size  : {len(RAG_TEST_QUERIES)} queries")
    print(f"  Threshold  : 0.40 (cosine distance)")
    print()

    if not GEMINI_API_KEY:
        print(f"  {colored('⚠️  GEMINI_API_KEY not set in .env — skipping API-based test', 'yellow')}")
        return None

    sys.path.insert(0, PROJECT_ROOT)
    from backend.integrations import gemini as gem
    from backend.integrations import chromadb_client as vdb

    RAG_SIMILARITY_THRESHOLD = 0.40

    correct = 0
    total = len(RAG_TEST_QUERIES)
    results = []

    for i, test in enumerate(RAG_TEST_QUERIES, 1):
        sys.stdout.write(f"\r  Testing... [{i}/{total}] ")
        sys.stdout.flush()

        query_embedding = gem.get_embedding(test["query"])
        chunks = vdb.search(query_embedding, n_results=5) if query_embedding else []

        relevant = [c for c in chunks if c["distance"] < RAG_SIMILARITY_THRESHOLD]
        found = len(relevant) > 0

        is_correct = (found == test["should_retrieve"])
        correct += int(is_correct)

        best_dist = min(c["distance"] for c in chunks) if chunks else float("inf")

        results.append({
            "query": test["query"],
            "topic": test["topic"],
            "expected": test["should_retrieve"],
            "got": found,
            "correct": is_correct,
            "best_distance": best_dist,
            "num_relevant": len(relevant),
        })

        time.sleep(0.3)

    accuracy = correct / total if total else 0
    print(f"\r  Testing... [{total}/{total}] ✅ Done!     ")

    print_subheader("Overall Results")
    acc_color = "green" if accuracy >= 0.85 else ("yellow" if accuracy >= 0.70 else "red")
    print(f"\n  {colored('Retrieval Accuracy', 'bold')} : {colored(f'{accuracy:.1%}', acc_color)}  "
          f"({correct}/{total} correct)")

    # ── Detail Table ──
    print_subheader("Per-Query Results")
    print(f"\n  {'Query':<45s} {'Expected':>9s} {'Got':>6s} {'Dist':>6s} {'':>3s}")
    print(f"  {'─'*75}")
    for r in results:
        status = colored("✅", "green") if r["correct"] else colored("❌", "red")
        exp = "Found" if r["expected"] else "None"
        got = "Found" if r["got"] else "None"
        dist = f"{r['best_distance']:.3f}" if r["best_distance"] != float("inf") else "  N/A"
        print(f"  {r['query'][:44]:<45s} {exp:>9s} {got:>6s} {dist:>6s} {status}")

    return accuracy


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN — RUN ALL EVALUATIONS
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("\n" + colored("=" * 60, "bold"))
    print(colored("  🏥 Healthcare Lead Agent — Model Evaluation", "bold"))
    print(colored("=" * 60, "bold"))
    print(f"  Project : Healthcare Lead Conversational Agent")
    print(f"  AI Model: Google Gemini 2.5 Flash (Few-Shot + RAG)")
    print(f"  Date    : {time.strftime('%Y-%m-%d %H:%M:%S')}")

    if not GEMINI_API_KEY:
        print(f"\n  {colored('⚠️  GEMINI_API_KEY is empty in .env', 'yellow')}")
        print(f"  {colored('   → Lead Qualifier tests will run (offline)', 'dim')}")
        print(f"  {colored('   → Intent & RAG tests will be skipped (need API key)', 'dim')}")

    scores = {}

    # 1. Lead Qualifier (offline — no API needed)
    scores["Lead Qualifier Validation"] = evaluate_lead_qualifier()

    # 2. Intent Classification (API-based)
    try:
        scores["Intent Classification"] = evaluate_intent_classification()
    except Exception as e:
        print(f"\n  ⚠️  Intent evaluation error: {e}")
        scores["Intent Classification"] = None

    # 3. RAG Retrieval (API-based + needs ChromaDB data)
    try:
        scores["RAG Retrieval"] = evaluate_rag_retrieval()
    except Exception as e:
        print(f"\n  ⚠️  RAG evaluation error: {e}")
        scores["RAG Retrieval"] = None

    # ═══ FINAL SUMMARY ═══
    print_header("📋 FINAL ACCURACY SUMMARY")
    print()
    print(f"  {'Component':<35s} {'Accuracy':>10s} {'Status':>8s}")
    print(f"  {'─'*55}")

    valid_scores = []
    for name, score in scores.items():
        if score is not None:
            color = "green" if score >= 0.85 else ("yellow" if score >= 0.70 else "red")
            status = "✅ PASS" if score >= 0.70 else "❌ FAIL"
            print(f"  {name:<35s} {colored(f'{score:>9.1%}', color)} {status:>8s}")
            valid_scores.append(score)
        else:
            print(f"  {name:<35s} {colored('   SKIPPED', 'yellow')} {'⚠️':>8s}")

    if valid_scores:
        overall = sum(valid_scores) / len(valid_scores)
        print(f"  {'─'*55}")
        overall_color = "green" if overall >= 0.85 else ("yellow" if overall >= 0.70 else "red")
        print(f"  {colored('Overall Average', 'bold'):<35s} {colored(f'{overall:>9.1%}', overall_color)}")

    print(f"\n  {'═'*55}")
    print()


if __name__ == "__main__":
    main()
