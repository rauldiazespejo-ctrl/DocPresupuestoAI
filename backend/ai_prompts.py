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
Eres un experto en presupuestos de construcción, servicios e ingeniería en Chile.

Con base en los datos extraídos del documento del cliente, genera un presupuesto COMPLETO y PROFESIONAL.

DATOS DEL PROYECTO:
{datos_proyecto}

INSTRUCCIONES:
1. Genera todas las partidas necesarias según el alcance del proyecto.
2. Usa precios de mercado chileno actualizados para {año}.
3. Incluye: materiales, mano de obra, equipos, gastos generales (15%), utilidades (10%), IVA (19%).
4. Si hay partidas ya definidas en las bases, úsalas como base y completa las faltantes.
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
    "total": 0
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
Eres un ingeniero senior con experiencia en proyectos de construcción e ingeniería en Chile.

Genera un INFORME TÉCNICO PROFESIONAL y COMPLETO basado en las bases del proyecto.

DATOS DEL PROYECTO:
{datos_proyecto}

El informe debe incluir:
1. Portada (datos del proyecto)
2. Introducción y Antecedentes
3. Alcance del Proyecto
4. Metodología de Trabajo
5. Descripción Técnica
6. Programa de Trabajo (carta Gantt simplificada)
7. Recursos Humanos y Equipos
8. Plan de Calidad
9. Plan de Seguridad
10. Conclusiones

Responde en formato Markdown profesional, usando el lenguaje técnico apropiado.

BASES DEL PROYECTO:
{texto_bases}
"""

# ─── Prompt para generar propuesta técnica ────────────────────────────────────
PROMPT_PROPUESTA_TECNICA = """
Eres un consultor experto en licitaciones en Chile. 

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
8. Compromisos y Garantías

Formato: Markdown profesional, redacción en primera persona plural (nosotros/nuestra empresa).

TEXTO DE LAS BASES:
{texto_bases}
"""

def build_prompt_analisis(texto: str) -> str:
    return PROMPT_ANALISIS_BASE.replace("{texto}", texto[:15000])

def build_prompt_presupuesto(datos_proyecto: dict, texto_bases: str, año: str = "2025") -> str:
    return PROMPT_GENERAR_PRESUPUESTO.replace(
        "{datos_proyecto}", json.dumps(datos_proyecto, ensure_ascii=False, indent=2)
    ).replace("{texto_bases}", texto_bases[:8000]).replace("{año}", año)

def build_prompt_informe(datos_proyecto: dict, texto_bases: str) -> str:
    return PROMPT_INFORME_TECNICO.replace(
        "{datos_proyecto}", json.dumps(datos_proyecto, ensure_ascii=False, indent=2)
    ).replace("{texto_bases}", texto_bases[:8000])

def build_prompt_propuesta(datos_proyecto: dict, texto_bases: str) -> str:
    return PROMPT_PROPUESTA_TECNICA.replace(
        "{datos_proyecto}", json.dumps(datos_proyecto, ensure_ascii=False, indent=2)
    ).replace("{texto_bases}", texto_bases[:8000])

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
