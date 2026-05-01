import openai
import anthropic
import json
import os
from backend.ai_prompts import (
    build_prompt_analisis, build_prompt_presupuesto,
    build_prompt_informe, build_prompt_propuesta, clean_json_response
)

class AIEngine:
    def __init__(self, provider: str = "openai", api_key: str = "", model: str = ""):
        self.provider = provider
        self.api_key = api_key
        
        if provider == "openai":
            self.model = model or "gpt-4o"
            self.client = openai.OpenAI(api_key=api_key)
        elif provider == "anthropic":
            self.model = model or "claude-3-5-sonnet-20241022"
            self.client = anthropic.Anthropic(api_key=api_key)

    def _call_llm(self, prompt: str, max_tokens: int = 4096) -> str:
        if self.provider == "openai":
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

    def generar_presupuesto(self, datos_proyecto: dict, texto_bases: str) -> dict:
        """Genera un presupuesto completo basado en las bases"""
        prompt = build_prompt_presupuesto(datos_proyecto, texto_bases)
        response = self._call_llm(prompt, max_tokens=4096)
        return clean_json_response(response)

    def generar_informe_tecnico(self, datos_proyecto: dict, texto_bases: str) -> str:
        """Genera el informe técnico en Markdown"""
        prompt = build_prompt_informe(datos_proyecto, texto_bases)
        return self._call_llm(prompt, max_tokens=4096)

    def generar_propuesta_tecnica(self, datos_proyecto: dict, texto_bases: str) -> str:
        """Genera la propuesta técnica en Markdown"""
        prompt = build_prompt_propuesta(datos_proyecto, texto_bases)
        return self._call_llm(prompt, max_tokens=4096)

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
