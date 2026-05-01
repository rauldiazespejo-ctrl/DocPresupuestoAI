import json
import re
from typing import Optional

# ─── Prompt maestro para análisis de bases ───────────────────────────────────
PROMPT_ANALISIS_BASE = """
Eres un experto en licitaciones, presupuestos técnicos y documentación contractual en Chile y Latinoamérica.

Analiza el siguiente documento (bases técnicas y/o administrativas) y extrae en formato JSON estricto la siguiente información:

{
  "proyecto": {
    "nombre": "",
    "descripcion": "",
    "mandante": "",
    "contratante": "",
    "plazo_ejecucion": "",
    "fecha_inicio": "",
    "fecha_termino": "",
    "moneda": "",
    "modalidad": "",
    "ubicacion": ""
  },
  "requisitos_tecnicos": [],
  "requisitos_administrativos": [],
  "partidas_presupuesto": [
    {
      "numero": "",
      "descripcion": "",
      "unidad": "",
      "cantidad": 0,
      "precio_unitario": 0,
      "observaciones": ""
    }
  ],
  "documentos_requeridos": [],
  "criterios_evaluacion": [],
  "garantias": [],
  "penalidades": [],
  "condiciones_pago": "",
  "contacto": {},
  "fechas_clave": {},
  "notas_importantes": []
}

IMPORTANTE: 
- Si no encuentras algún campo, usa null o lista vacía.
- Para las partidas de presupuesto, si el documento incluye ítems numerados, extráelos TODOS.
- Detecta la moneda (CLP, UF, USD) y úsala consistentemente.
- Responde SOLO con el JSON, sin texto adicional.

DOCUMENTO A ANALIZAR:
\"\"\"
{texto}
\"\"\"
"""

# ─── Prompt para generar presupuesto completo ──────────────────────────────────
PROMPT_GENERAR_PRESUPUESTO = """
Actúa como gerente de estudios y propuestas senior, experto en presupuestos de construcción, servicios e ingeniería en Chile.

Con base en los datos extraídos del documento del cliente, genera un presupuesto COMPLETO, PROFESIONAL y LISTO PARA PRESENTACIÓN A CLIENTE.

DATOS DEL PROYECTO:
{datos_proyecto}

INSTRUCCIONES:
1. Genera todas las partidas necesarias según el alcance del proyecto.
2. Usa precios de mercado chileno actualizados para {año}, con criterio conservador y defendible.
3. Incluye: materiales, mano de obra, equipos, gastos generales (15%), utilidades (10%), IVA (19%).
4. Si hay partidas ya definidas en las bases, úsalas como base y completa las faltantes.
5. Usa nombres de partidas claros y ejecutivos.
6. No inventes condiciones contractuales específicas no presentes; cuando falten, propone supuestos razonables explícitos.
5. Responde en JSON con esta estructura:

{
  "resumen": {
    "nombre_proyecto": "",
    "cliente": "",
    "fecha": "",
    "moneda": "CLP",
    "subtotal": 0,
    "gastos_generales": 0,
    "utilidades": 0,
    "neto": 0,
    "iva": 0,
    "total": 0,
    "validez_oferta": "30 días corridos",
    "plazo_ejecucion": "plazo sugerido de ejecución",
    "supuestos": "supuestos clave del presupuesto en una sola frase"
  },
  "partidas": [
    {
      "numero": "1",
      "partida": "Nombre de la partida",
      "descripcion": "Descripción detallada",
      "unidad": "m2/ml/gl/un",
      "cantidad": 0,
      "precio_unitario": 0,
      "precio_total": 0,
      "categoria": "obra_civil/electricidad/etc"
    }
  ]
}

TEXTO DE LAS BASES:
{texto_bases}
"""

# ─── Prompt para generar informe técnico ──────────────────────────────────────
PROMPT_INFORME_TECNICO = """
Eres un gerente técnico senior con experiencia en ingeniería y licitaciones en Chile.

Genera un INFORME TÉCNICO PROFESIONAL, EJECUTIVO y COMPLETO basado en las bases del proyecto.

DATOS DEL PROYECTO:
{datos_proyecto}

El informe debe incluir:
1. Portada (datos del proyecto)
2. Resumen Ejecutivo (máximo 8 líneas, orientado a decisión)
3. Introducción y Antecedentes
3. Alcance del Proyecto
4. Metodología de Trabajo
5. Descripción Técnica
6. Programa de Trabajo (carta Gantt simplificada)
7. Recursos Humanos y Equipos
8. Plan de Calidad
9. Plan de Seguridad
10. Riesgos y Mitigaciones
11. Supuestos y Exclusiones
12. Conclusiones y Recomendación

CRITERIOS DE REDACCIÓN:
- Español profesional de nivel corporativo.
- Oraciones claras y trazables a bases.
- Evita frases vagas o marketing vacío.
- Incluye bullets accionables cuando corresponda.

Responde en formato Markdown profesional, usando el lenguaje técnico apropiado.

BASES DEL PROYECTO:
{texto_bases}
"""

# ─── Prompt para generar propuesta técnica ────────────────────────────────────
PROMPT_PROPUESTA_TECNICA = """
Eres director de propuestas y licitaciones en Chile.

Genera una PROPUESTA TÉCNICA COMPLETA Y GANADORA para el siguiente proyecto.

La propuesta debe ser convincente, profesional y responder a TODOS los requisitos de las bases.

DATOS EXTRAÍDOS:
{datos_proyecto}

Estructura:
1. Resumen Ejecutivo
2. Comprensión del Proyecto
3. Enfoque y Metodología
4. Experiencia Relevante
5. Equipo de Trabajo Propuesto
6. Plan de Trabajo y Cronograma
7. Gestión de Riesgos
8. Plan de Calidad y Seguridad
9. Supuestos, Exclusiones y Dependencias
10. Compromisos y Garantías
11. Cierre Ejecutivo (propuesta de valor concreta)

Formato: Markdown profesional, redacción en primera persona plural (nosotros/nuestra empresa).

TEXTO DE LAS BASES:
{texto_bases}
"""

def build_prompt_analisis(texto: str) -> str:
    return PROMPT_ANALISIS_BASE.replace("{texto}", texto[:15000])

def _quality_directive(quality_mode: str = "standard") -> str:
    mode = (quality_mode or "standard").strip().lower()
    if mode == "pro":
        return (
            "\nMODO PRO ACTIVADO:\n"
            "- Eleva profundidad técnica y claridad ejecutiva.\n"
            "- Refuerza trazabilidad de supuestos y riesgos.\n"
            "- Prioriza calidad de entrega para cliente final.\n"
        )
    return "\nMODO STANDARD: entrega clara y correcta.\n"


def build_prompt_presupuesto(
    datos_proyecto: dict, texto_bases: str, año: str = "2025", quality_mode: str = "standard"
) -> str:
    return (
        PROMPT_GENERAR_PRESUPUESTO.replace(
        "{datos_proyecto}", json.dumps(datos_proyecto, ensure_ascii=False, indent=2)
        ).replace("{texto_bases}", texto_bases[:8000]).replace("{año}", año)
        + _quality_directive(quality_mode)
    )

def build_prompt_informe(datos_proyecto: dict, texto_bases: str, quality_mode: str = "standard") -> str:
    return (
        PROMPT_INFORME_TECNICO.replace(
        "{datos_proyecto}", json.dumps(datos_proyecto, ensure_ascii=False, indent=2)
        ).replace("{texto_bases}", texto_bases[:8000])
        + _quality_directive(quality_mode)
    )

def build_prompt_propuesta(datos_proyecto: dict, texto_bases: str, quality_mode: str = "standard") -> str:
    return (
        PROMPT_PROPUESTA_TECNICA.replace(
        "{datos_proyecto}", json.dumps(datos_proyecto, ensure_ascii=False, indent=2)
        ).replace("{texto_bases}", texto_bases[:8000])
        + _quality_directive(quality_mode)
    )


def ensure_professional_markdown_structure(text: str, kind: str = "informe") -> str:
    """
    Asegura una estructura mínima profesional para entregables markdown.
    Si la IA no trae secciones críticas, agrega placeholders ejecutivos.
    """
    raw = (text or "").strip()
    if not raw:
        raw = "# Documento\n\nContenido no disponible."

    lower = raw.lower()
    additions = []
    if kind == "informe":
        required = [
            ("## Resumen Ejecutivo", "Pendiente de completar resumen ejecutivo."),
            ("## Riesgos y Mitigaciones", "Sin riesgos explicitados por la IA."),
            ("## Supuestos y Exclusiones", "Sin supuestos/exclusiones explicitados por la IA."),
            ("## Conclusiones y Recomendación", "Sin recomendación final explicitada por la IA."),
        ]
    else:
        required = [
            ("## Resumen Ejecutivo", "Pendiente de completar resumen ejecutivo."),
            ("## Plan de Calidad y Seguridad", "Sin plan de calidad/seguridad explicitado por la IA."),
            ("## Supuestos, Exclusiones y Dependencias", "Sin supuestos/exclusiones/dependencias explicitados por la IA."),
            ("## Cierre Ejecutivo", "Sin cierre ejecutivo explicitado por la IA."),
        ]

    for title, fallback in required:
        if title.lower() not in lower:
            additions.append(f"\n{title}\n\n{fallback}\n")

    return raw + "".join(additions)

def clean_json_response(text: str) -> dict:
    """Limpia y parsea respuesta JSON de la IA"""
    # Eliminar markdown code blocks
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()
    
    # Buscar JSON válido
    start = text.find('{')
    end = text.rfind('}') + 1
    if start >= 0 and end > start:
        text = text[start:end]
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"error": "No se pudo parsear la respuesta", "raw": text[:500]}
