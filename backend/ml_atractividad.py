import math
from typing import Dict, List, Tuple


def _sigmoid(x: float) -> float:
    if x < -60:
        return 0.0
    if x > 60:
        return 1.0
    return 1.0 / (1.0 + math.exp(-x))


def _safe_std(values: List[float], mean: float) -> float:
    if not values:
        return 1.0
    var = sum((v - mean) ** 2 for v in values) / len(values)
    std = math.sqrt(var)
    return std if std > 1e-9 else 1.0


def _split_train_val(rows: List[Dict], ratio: float = 0.8) -> Tuple[List[Dict], List[Dict]]:
    if len(rows) <= 1:
        return rows, rows
    cut = max(1, int(len(rows) * ratio))
    return rows[:cut], rows[cut:]


def _accuracy(weights: List[float], bias: float, x: List[List[float]], y: List[int]) -> float:
    if not y:
        return 0.0
    ok = 0
    for i, row in enumerate(x):
        z = sum(weights[j] * row[j] for j in range(len(weights))) + bias
        pred = 1 if _sigmoid(z) >= 0.5 else 0
        if pred == y[i]:
            ok += 1
    return ok / len(y)


def _rates(historico: List[Dict]) -> Tuple[Dict[str, float], Dict[str, float], float]:
    total = max(1, len(historico))
    global_rate = sum(1 for h in historico if h.get("fue_adjudicada")) / total

    cliente_sum: Dict[str, int] = {}
    cliente_cnt: Dict[str, int] = {}
    rubro_sum: Dict[str, int] = {}
    rubro_cnt: Dict[str, int] = {}
    for h in historico:
        y = 1 if h.get("fue_adjudicada") else 0
        c = (h.get("cliente") or "").strip().lower()
        r = (h.get("rubro") or "").strip().lower()
        if c:
            cliente_sum[c] = cliente_sum.get(c, 0) + y
            cliente_cnt[c] = cliente_cnt.get(c, 0) + 1
        if r:
            rubro_sum[r] = rubro_sum.get(r, 0) + y
            rubro_cnt[r] = rubro_cnt.get(r, 0) + 1

    cliente_rate = {k: cliente_sum[k] / max(1, cliente_cnt[k]) for k in cliente_cnt}
    rubro_rate = {k: rubro_sum[k] / max(1, rubro_cnt[k]) for k in rubro_cnt}
    return cliente_rate, rubro_rate, global_rate


def build_features(h: Dict, cliente_rate: Dict[str, float], rubro_rate: Dict[str, float], global_rate: float) -> List[float]:
    monto = float(h.get("monto_ofertado", 0.0) or 0.0)
    margen = float(h.get("margen_pct", 0.0) or 0.0)
    c = (h.get("cliente") or "").strip().lower()
    r = (h.get("rubro") or "").strip().lower()
    c_rate = cliente_rate.get(c, global_rate)
    r_rate = rubro_rate.get(r, global_rate)
    return [math.log1p(max(0.0, monto)), margen, c_rate * 100.0, r_rate * 100.0]


def train_logistic_model(historico: List[Dict], epochs: int = 800, lr: float = 0.02) -> Dict:
    if len(historico) < 12:
        return {
            "ok": False,
            "error": "Se requieren al menos 12 registros historicos para entrenar ML v2.",
        }

    cliente_rate, rubro_rate, global_rate = _rates(historico)
    rows = [
        {
            "x": build_features(h, cliente_rate, rubro_rate, global_rate),
            "y": 1 if h.get("fue_adjudicada") else 0,
        }
        for h in historico
    ]
    train_rows, val_rows = _split_train_val(rows, ratio=0.8)
    x_train = [r["x"] for r in train_rows]
    y_train = [r["y"] for r in train_rows]
    x_val = [r["x"] for r in val_rows]
    y_val = [r["y"] for r in val_rows]

    # Normalizacion simple.
    cols = list(zip(*x_train))
    means = [sum(col) / len(col) for col in cols]
    stds = [_safe_std(list(col), means[idx]) for idx, col in enumerate(cols)]

    def norm(row: List[float]) -> List[float]:
        return [(row[i] - means[i]) / stds[i] for i in range(len(row))]

    x_train_n = [norm(row) for row in x_train]
    x_val_n = [norm(row) for row in x_val] if x_val else []

    n_features = len(x_train_n[0])
    w = [0.0] * n_features
    b = 0.0

    for _ in range(max(50, epochs)):
        grad_w = [0.0] * n_features
        grad_b = 0.0
        m = len(x_train_n)
        for i, row in enumerate(x_train_n):
            z = sum(w[j] * row[j] for j in range(n_features)) + b
            p = _sigmoid(z)
            err = p - y_train[i]
            for j in range(n_features):
                grad_w[j] += err * row[j]
            grad_b += err
        for j in range(n_features):
            w[j] -= lr * (grad_w[j] / m)
        b -= lr * (grad_b / m)

    acc_train = _accuracy(w, b, x_train_n, y_train)
    acc_val = _accuracy(w, b, x_val_n, y_val) if y_val else acc_train

    return {
        "ok": True,
        "model": {
            "weights": w,
            "bias": b,
            "means": means,
            "stds": stds,
            "feature_names": ["log_monto", "margen_pct", "cliente_win_rate", "rubro_win_rate"],
            "cliente_rates": cliente_rate,
            "rubro_rates": rubro_rate,
            "global_win_rate": global_rate,
            "train_size": len(x_train),
            "val_size": len(x_val),
            "accuracy_train": round(acc_train, 4),
            "accuracy_val": round(acc_val, 4),
        },
    }


def predict_atractividad_ml(model: Dict, cliente: str, rubro: str, monto_oferta: float, margen_pct: float) -> Dict:
    cliente_rates = model.get("cliente_rates", {})
    rubro_rates = model.get("rubro_rates", {})
    global_rate = float(model.get("global_win_rate", 0.5))

    row = {
        "cliente": cliente,
        "rubro": rubro,
        "monto_ofertado": monto_oferta,
        "margen_pct": margen_pct,
    }
    raw = build_features(row, cliente_rates, rubro_rates, global_rate)
    means = model.get("means", [0, 0, 0, 0])
    stds = model.get("stds", [1, 1, 1, 1])
    x = [(raw[i] - means[i]) / (stds[i] if stds[i] != 0 else 1.0) for i in range(len(raw))]

    w = model.get("weights", [0, 0, 0, 0])
    b = float(model.get("bias", 0.0))
    z = sum(w[i] * x[i] for i in range(len(w))) + b
    p = _sigmoid(z)
    score = max(0.0, min(100.0, p * 100.0))

    if score >= 75:
        decision = "go_fuerte"
    elif score >= 60:
        decision = "go_condicionado"
    else:
        decision = "no_go"

    return {
        "score_atractividad_ml": round(score, 2),
        "probabilidad_ml": round(p, 4),
        "decision_ml": decision,
        "features": {
            "log_monto": round(raw[0], 4),
            "margen_pct": round(raw[1], 4),
            "cliente_win_rate": round(raw[2], 4),
            "rubro_win_rate": round(raw[3], 4),
        },
    }
