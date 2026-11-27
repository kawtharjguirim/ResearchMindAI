"""ROUGE-1, ROUGE-2 et ROUGE-L (implementation compacte, sans dependance externe).

ROUGE-N : recouvrement de n-grammes (avec clipping, comme BLEU) entre un texte genere
(hypothese) et un texte de reference. ROUGE-L : plus longue sous-sequence commune (LCS).
Chacun est rapporte en precision / rappel / f1.
"""
import re
from collections import Counter


def _tokeniser(texte):
    return re.findall(r"\w+", texte.lower())


def _ngrams(tokens, n):
    return [tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def _p_r_f1(overlap, n_hyp, n_ref):
    p = overlap / n_hyp if n_hyp else 0.0
    r = overlap / n_ref if n_ref else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return {"precision": p, "rappel": r, "f1": f1}


def rouge_n(hyp, ref, n):
    h, r = _ngrams(_tokeniser(hyp), n), _ngrams(_tokeniser(ref), n)
    if not h or not r:
        return {"precision": 0.0, "rappel": 0.0, "f1": 0.0}
    cr = Counter(r)
    overlap = sum(min(c, cr[g]) for g, c in Counter(h).items())
    return _p_r_f1(overlap, len(h), len(r))


def _lcs(a, b):
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            dp[i][j] = dp[i - 1][j - 1] + 1 if a[i - 1] == b[j - 1] else max(dp[i - 1][j], dp[i][j - 1])
    return dp[-1][-1]


def rouge_l(hyp, ref):
    h, r = _tokeniser(hyp), _tokeniser(ref)
    if not h or not r:
        return {"precision": 0.0, "rappel": 0.0, "f1": 0.0}
    return _p_r_f1(_lcs(h, r), len(h), len(r))


def rouge(hyp, ref):
    """{"rouge-1": {precision, rappel, f1}, "rouge-2": {...}, "rouge-l": {...}}"""
    return {"rouge-1": rouge_n(hyp, ref, 1), "rouge-2": rouge_n(hyp, ref, 2), "rouge-l": rouge_l(hyp, ref)}
