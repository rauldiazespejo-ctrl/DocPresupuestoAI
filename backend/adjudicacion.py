from typing import Dict, List


def _clamp(value: float, min_value: float = 0.0, max_value: float = 100.0) -> float:
    return max(min_value, min(max_value, float(value)))


def _infer_base_factors(datos_extraidos: Dict) -> Dict[str, float]:
    proyecto = datos_extraidos.get("proyecto", {}) if isinstance(datos_extraidos, dict) else {}
    requisitos_admin = datos_extraidos.get("requisitos_administrativos", []) if isinstance(datos_extraidos, dict) else []
    documentos_req = datos_extraidos.get("documentos_requeridos", []) if isinstance(datos_extraidos, dict) else []
    plazo = proyecto.get("plazo_dias", 0) or 0

    # Heuristica inicial para arrancar sin historico real.
    cumplimiento_requisitos = 65.0 if (requisitos_admin or documentos_req) else 55.0
    competitividad_precio = 60.0
    solidez_tecnica = 62.0 if proyecto else 55.0
    solidez_hse = 58.0
    riesgo_contractual = 45.0 if plazo and plazo > 0 else 55.0

    return {
        "cumplimiento_requisitos": cumplimiento_requisitos,
        "competitividad_precio": competitividad_precio,
        "solidez_tecnica": solidez_tecnica,
        "solidez_hse": solidez_hse,
        "riesgo_contractual": riesgo_contractual,
    }


def calcular_prediccion(datos_extraidos: Dict, factores_usuario: Dict) -> Dict:
    base = _infer_base_factors(datos_extraidos)
    factores_usuario = factores_usuario or {}

    factores = {
        "cumplimiento_requisitos": _clamp(factores_usuario.get("cumplimiento_requisitos", base["cumplimiento_requisitos"])),
        "competitividad_precio": _clamp(factores_usuario.get("competitividad_precio", base["competitividad_precio"])),
        "solidez_tecnica": _clamp(factores_usuario.get("solidez_tecnica", base["solidez_tecnica"])),
        "solidez_hse": _clamp(factores_usuario.get("solidez_hse", base["solidez_hse"])),
        "riesgo_contractual": _clamp(factores_usuario.get("riesgo_contractual", base["riesgo_contractual"])),
    }

    pesos = {
        "cumplimiento_requisitos": 0.25,
        "competitividad_precio": 0.25,
        "solidez_tecnica": 0.20,
        "solidez_hse": 0.15,
        "riesgo_contractual_invertido": 0.15,
    }

    riesgo_invertido = 100.0 - factores["riesgo_contractual"]
    score_base = (
        factores["cumplimiento_requisitos"] * pesos["cumplimiento_requisitos"]
        + factores["competitividad_precio"] * pesos["competitividad_precio"]
        + factores["solidez_tecnica"] * pesos["solidez_tecnica"]
        + factores["solidez_hse"] * pesos["solidez_hse"]
        + riesgo_invertido * pesos["riesgo_contractual_invertido"]
    )
    score_base = round(_clamp(score_base), 2)

    # Analisis de riesgo cuantitativo "risk-like" (probabilidad x impacto).
    matriz_riesgos, indice_riesgo = _construir_matriz_riesgos(factores)
    penalizacion = min(25.0, indice_riesgo * 0.35)
    score = round(_clamp(score_base - penalizacion), 2)
    probabilidad = round(score / 100.0, 4)
    escenarios = _calcular_escenarios(score, indice_riesgo)

    drivers = [
        ("cumplimiento_requisitos", factores["cumplimiento_requisitos"]),
        ("competitividad_precio", factores["competitividad_precio"]),
        ("solidez_tecnica", factores["solidez_tecnica"]),
        ("solidez_hse", factores["solidez_hse"]),
        ("riesgo_contractual", 100.0 - factores["riesgo_contractual"]),
    ]
    drivers_ordenados = sorted(drivers, key=lambda x: x[1], reverse=True)
    top_positivos = [{"factor": nombre, "puntaje": round(valor, 2)} for nombre, valor in drivers_ordenados[:3]]
    top_negativos = [{"factor": nombre, "puntaje": round(valor, 2)} for nombre, valor in drivers_ordenados[-2:]]

    recomendaciones = _construir_recomendaciones(factores)

    return {
        "score_base": score_base,
        "score": score,
        "probabilidad_adjudicacion": probabilidad,
        "factores": factores,
        "indice_riesgo": round(indice_riesgo, 2),
        "matriz_riesgos": matriz_riesgos,
        "escenarios": escenarios,
        "penalizacion_riesgo": round(penalizacion, 2),
        "top_factores_positivos": top_positivos,
        "top_factores_negativos": top_negativos,
        "recomendaciones": recomendaciones,
        "version_modelo": "rules-risk-v2",
    }


def _construir_recomendaciones(factores: Dict[str, float]) -> List[str]:
    recomendaciones: List[str] = []
    if factores["cumplimiento_requisitos"] < 70:
        recomendaciones.append("Subir cumplimiento documental tecnico/administrativo y cerrar brechas criticas antes de ofertar.")
    if factores["competitividad_precio"] < 70:
        recomendaciones.append("Revisar estructura de costos y optimizar partidas de mayor impacto economico.")
    if factores["solidez_tecnica"] < 70:
        recomendaciones.append("Reforzar metodologia, recursos clave y evidencia tecnica de experiencia similar.")
    if factores["solidez_hse"] < 70:
        recomendaciones.append("Completar matriz de riesgos, controles HSE y evidencias de cumplimiento normativo.")
    if factores["riesgo_contractual"] > 45:
        recomendaciones.append("Mitigar exposicion contractual: multas, garantias, hitos y condiciones de pago.")
    if not recomendaciones:
        recomendaciones.append("Oferta competitiva. Mantener trazabilidad y respaldo documental para sustentacion final.")
    return recomendaciones


def _construir_matriz_riesgos(factores: Dict[str, float]) -> tuple[list[Dict], float]:
    # Escala 1-5 de probabilidad e impacto, derivada de factores de oferta.
    p_doc = _escala_1_5(100.0 - factores["cumplimiento_requisitos"])
    i_doc = _escala_1_5(80.0)

    p_tecnico = _escala_1_5(100.0 - factores["solidez_tecnica"])
    i_tecnico = _escala_1_5(90.0)

    p_hse = _escala_1_5(100.0 - factores["solidez_hse"])
    i_hse = _escala_1_5(95.0)

    p_precio = _escala_1_5(100.0 - factores["competitividad_precio"])
    i_precio = _escala_1_5(85.0)

    p_contractual = _escala_1_5(factores["riesgo_contractual"])
    i_contractual = _escala_1_5(92.0)

    matriz = [
        _riesgo("documental_administrativo", p_doc, i_doc),
        _riesgo("tecnico_operacional", p_tecnico, i_tecnico),
        _riesgo("hse_seguridad", p_hse, i_hse),
        _riesgo("economico_precio", p_precio, i_precio),
        _riesgo("contractual_legal", p_contractual, i_contractual),
    ]

    indice = 0.0
    pesos = {
        "documental_administrativo": 0.18,
        "tecnico_operacional": 0.22,
        "hse_seguridad": 0.20,
        "economico_precio": 0.20,
        "contractual_legal": 0.20,
    }
    for r in matriz:
        # Riesgo normalizado 0..100 desde (P*I) 1..25
        severidad = ((r["probabilidad"] * r["impacto"]) / 25.0) * 100.0
        indice += severidad * pesos[r["riesgo"]]
    return matriz, _clamp(indice)


def _escala_1_5(valor_0_100: float) -> int:
    v = _clamp(valor_0_100)
    if v < 20:
        return 1
    if v < 40:
        return 2
    if v < 60:
        return 3
    if v < 80:
        return 4
    return 5


def _nivel_riesgo(probabilidad: int, impacto: int) -> str:
    producto = probabilidad * impacto
    if producto >= 16:
        return "alto"
    if producto >= 9:
        return "medio"
    return "bajo"


def _riesgo(nombre: str, probabilidad: int, impacto: int) -> Dict:
    return {
        "riesgo": nombre,
        "probabilidad": probabilidad,
        "impacto": impacto,
        "nivel": _nivel_riesgo(probabilidad, impacto),
    }


def _calcular_escenarios(score: float, indice_riesgo: float) -> Dict:
    # Escenarios de confianza tipo P10/P50/P90 simplificado.
    ajuste_conservador = min(20.0, (indice_riesgo / 100.0) * 18.0 + 3.0)
    ajuste_agresivo = max(4.0, 10.0 - (indice_riesgo / 100.0) * 5.0)

    score_pesimista = _clamp(score - ajuste_conservador)
    score_base = _clamp(score)
    score_optimista = _clamp(score + ajuste_agresivo)

    return {
        "pesimista": {
            "score": round(score_pesimista, 2),
            "probabilidad": round(score_pesimista / 100.0, 4),
        },
        "base": {
            "score": round(score_base, 2),
            "probabilidad": round(score_base / 100.0, 4),
        },
        "optimista": {
            "score": round(score_optimista, 2),
            "probabilidad": round(score_optimista / 100.0, 4),
        },
    }


def calcular_atractividad_licitacion(
    prediccion_actual: Dict,
    historico_3y: List[Dict],
    cliente_objetivo: str = ""
) -> Dict:
    total = len(historico_3y)
    ganadas = sum(1 for h in historico_3y if h.get("fue_adjudicada"))
    win_rate = (ganadas / total * 100.0) if total else 0.0

    cliente_obj = (cliente_objetivo or "").strip().lower()
    hist_cliente = [h for h in historico_3y if (h.get("cliente", "") or "").strip().lower() == cliente_obj] if cliente_obj else []
    total_cliente = len(hist_cliente)
    ganadas_cliente = sum(1 for h in hist_cliente if h.get("fue_adjudicada"))
    win_rate_cliente = (ganadas_cliente / total_cliente * 100.0) if total_cliente else win_rate

    margen_values = [float(h.get("margen_pct", 0.0) or 0.0) for h in historico_3y]
    margen_promedio = sum(margen_values) / len(margen_values) if margen_values else 0.0

    score_actual = float(prediccion_actual.get("score", 0.0) or 0.0)
    indice_riesgo = float(prediccion_actual.get("indice_riesgo", 50.0) or 50.0)
    riesgo_invertido = 100.0 - _clamp(indice_riesgo)

    # "ML-ready v1": mezcla del score actual + prior histórico (3 años).
    score_atractividad = (
        score_actual * 0.45
        + win_rate * 0.25
        + win_rate_cliente * 0.20
        + riesgo_invertido * 0.10
    )

    # Ajuste por tamaño de muestra (evitar sobreconfianza con pocos datos).
    factor_confianza = min(1.0, total / 30.0) if total > 0 else 0.2
    score_atractividad = score_atractividad * (0.6 + 0.4 * factor_confianza)
    score_atractividad = round(_clamp(score_atractividad), 2)

    if score_atractividad >= 75:
        decision = "go_fuerte"
        recomendacion = "Licitacion atractiva. Avanzar agresivamente con oferta competitiva y cierre de brechas menores."
    elif score_atractividad >= 60:
        decision = "go_condicionado"
        recomendacion = "Licitacion medianamente atractiva. Ir solo si se mitigan riesgos clave y se valida margen objetivo."
    else:
        decision = "no_go"
        recomendacion = "Licitacion poco atractiva bajo condiciones actuales. Recomendado no ofertar o reformular estrategia."

    return {
        "score_atractividad": score_atractividad,
        "probabilidad_adjudicacion_ajustada": round(score_atractividad / 100.0, 4),
        "decision": decision,
        "recomendacion": recomendacion,
        "metricas_historicas": {
            "muestra_3y": total,
            "win_rate_3y": round(win_rate, 2),
            "win_rate_cliente_objetivo": round(win_rate_cliente, 2),
            "margen_promedio_pct": round(margen_promedio, 2),
            "factor_confianza_muestra": round(factor_confianza, 2),
        },
        "base_prediccion_actual": {
            "score": round(score_actual, 2),
            "indice_riesgo": round(indice_riesgo, 2),
            "version_modelo": prediccion_actual.get("version_modelo", "rules-risk-v2"),
        },
        "version_modelo_atractividad": "ml-ready-v1",
    }
