import openai
import anthropic
import json
import os
from backend.ai_prompts import (
    build_prompt_analisis, build_prompt_presupuesto,
    build_prompt_informe, build_prompt_propuesta, clean_json_response,
    ensure_professional_markdown_structure
)

class AIEngine:
    def __init__(self, provider: str = "openai", api_key: str = "", model: str = ""):
        self.provider = provider
        self.api_key = api_key
        
        if provider == "openai":
            self.model = model or "gpt-4o"
            self.client = openai.OpenAI(api_key=api_key)
        elif provider == "zai":
            # ZAI expone API compatible con OpenAI Chat Completions.
            self.model = model or "glm-4.5-air"
            self.client = openai.OpenAI(
                api_key=api_key,
                base_url=os.getenv("ZAI_BASE_URL", "https://api.z.ai/api/paas/v4")
            )
        elif provider == "anthropic":
            self.model = model or "claude-3-5-sonnet-20241022"
            self.client = anthropic.Anthropic(api_key=api_key)

    def _call_llm(self, prompt: str, max_tokens: int = 4096) -> str:
        if self.provider in {"openai", "zai"}:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.3
            )
            return response.choices[0].message.content
        
        elif self.provider == "anthropic":
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        
        return ""

    def analizar_bases(self, texto: str) -> dict:
        """Analiza las bases del proyecto y extrae información clave"""
        prompt = build_prompt_analisis(texto)
        response = self._call_llm(prompt, max_tokens=4096)
        return clean_json_response(response)

    def generar_presupuesto(self, datos_proyecto: dict, texto_bases: str, quality_mode: str = "standard") -> dict:
        """Genera un presupuesto completo basado en las bases"""
        prompt = build_prompt_presupuesto(datos_proyecto, texto_bases, quality_mode=quality_mode)
        response = self._call_llm(prompt, max_tokens=4096)
        parsed = clean_json_response(response)

        # Normalización mínima para entregar JSON utilizable al generador.
        if not isinstance(parsed, dict):
            parsed = {}
        resumen = parsed.get("resumen") or {}
        if not isinstance(resumen, dict):
            resumen = {}
        resumen.setdefault("nombre_proyecto", (datos_proyecto.get("proyecto") or {}).get("nombre", "Proyecto"))
        resumen.setdefault("cliente", (datos_proyecto.get("proyecto") or {}).get("mandante", "Cliente no informado"))
        resumen.setdefault("fecha", "")
        resumen.setdefault("moneda", (datos_proyecto.get("proyecto") or {}).get("moneda", "CLP") or "CLP")
        resumen.setdefault("validez_oferta", "30 días corridos")
        resumen.setdefault("plazo_ejecucion", (datos_proyecto.get("proyecto") or {}).get("plazo_ejecucion", "Según bases"))
        resumen.setdefault(
            "supuestos",
            "Sujeto a validación de alcance definitivo, accesos operativos y antecedentes complementarios del cliente.",
        )
        parsed["resumen"] = resumen
        if not isinstance(parsed.get("partidas"), list):
            parsed["partidas"] = []
        return parsed

    def generar_informe_tecnico(self, datos_proyecto: dict, texto_bases: str, quality_mode: str = "standard") -> str:
        """Genera el informe técnico en Markdown"""
        prompt = build_prompt_informe(datos_proyecto, texto_bases, quality_mode=quality_mode)
        raw = self._call_llm(prompt, max_tokens=4096)
        return ensure_professional_markdown_structure(raw, kind="informe")

    def generar_propuesta_tecnica(self, datos_proyecto: dict, texto_bases: str, quality_mode: str = "standard") -> str:
        """Genera la propuesta técnica en Markdown"""
        prompt = build_prompt_propuesta(datos_proyecto, texto_bases, quality_mode=quality_mode)
        raw = self._call_llm(prompt, max_tokens=4096)
        return ensure_professional_markdown_structure(raw, kind="propuesta")

    def consulta_libre(self, pregunta: str, contexto: str) -> str:
        """Consulta libre sobre el documento"""
        prompt = f"""
Eres un experto en licitaciones y presupuestos técnicos.

CONTEXTO DEL PROYECTO:
{contexto[:6000]}

PREGUNTA DEL USUARIO:
{pregunta}

Responde de forma clara, técnica y profesional en español.
"""
        return self._call_llm(prompt, max_tokens=2048)
