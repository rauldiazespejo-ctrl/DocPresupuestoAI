import openai
import anthropic
import json
import os
from backend.ai_prompts import (
    build_prompt_analisis, build_prompt_presupuesto,
    build_prompt_informe, build_prompt_propuesta, clean_json_response,
    ensure_professional_markdown_structure
)


class IAAuthError(Exception):
    """API key rechazada o expirada (401)."""


class IARateLimitError(Exception):
    """Cuota o límite de velocidad del proveedor."""


def _auth_message(provider: str) -> str:
    if provider == "zai":
        return (
            "ZAI respondió 401 (token incorrecto o expirado). "
            "Genera una API key válida en el panel de Z.AI y pégala en «Configurar IA» (modelo GLM acorde a tu plan)."
        )
    if provider == "openai":
        return (
            "OpenAI respondió 401 (API key inválida o revocada). "
            "Revisa la clave en https://platform.openai.com y actualízala en «Configurar IA»."
        )
    if provider == "gemini":
        return (
            "Gemini rechazó la API key (403/401). "
            "Crea una clave en https://aistudio.google.com/app/apikey (Google AI Studio), "
            "no uses la contraseña de cuenta: pégala en «Configurar IA»."
        )
    return (
        "El proveedor de IA rechazó la autenticación (401). "
        "Actualiza la API key en «Configurar IA»."
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
        elif provider == "gemini":
            try:
                import google.generativeai as genai
            except ImportError as e:
                raise RuntimeError(
                    "Falta el paquete google-generativeai. Ejecuta: pip install google-generativeai"
                ) from e
            genai.configure(api_key=api_key)
            self.model = model or "gemini-2.0-flash"
            self.client = None
            self._gemini = genai.GenerativeModel(self.model)
        else:
            raise ValueError(
                f"Proveedor de IA no soportado: {provider!r}. "
                "Usa: openai, zai, anthropic o gemini."
            )

    def _call_gemini(self, prompt: str, max_tokens: int) -> str:
        from google.api_core import exceptions as google_exc

        try:
            resp = self._gemini.generate_content(
                prompt,
                generation_config={
                    "max_output_tokens": max_tokens,
                    "temperature": 0.3,
                },
            )
        except google_exc.PermissionDenied as e:
            raise IAAuthError(_auth_message("gemini")) from e
        except google_exc.Unauthenticated as e:
            raise IAAuthError(_auth_message("gemini")) from e
        except google_exc.ResourceExhausted as e:
            raise IARateLimitError(
                "Límite de uso en Gemini (429). Espera unos minutos o revisa cuota en Google AI Studio."
            ) from e
        except google_exc.GoogleAPIError as e:
            raise RuntimeError(f"Error API Gemini: {e}") from e

        if not getattr(resp, "candidates", None):
            raise RuntimeError(
                "Gemini no devolvió candidatos (bloqueo de seguridad o prompt vacío). "
                "Acorta el texto o revisa el contenido."
            )
        text = (getattr(resp, "text", None) or "").strip()
        if not text:
            raise RuntimeError("Gemini devolvió respuesta vacía. Reintenta o cambia de modelo.")
        return text

    def _call_llm(self, prompt: str, max_tokens: int = 4096) -> str:
        try:
            if self.provider == "gemini":
                return self._call_gemini(prompt, max_tokens)

            if self.provider in {"openai", "zai"}:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=0.3,
                )
                return response.choices[0].message.content or ""

            if self.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.content[0].text

            return ""
        except openai.AuthenticationError as e:
            raise IAAuthError(_auth_message(self.provider)) from e
        except openai.APIStatusError as e:
            if e.status_code == 401:
                raise IAAuthError(_auth_message(self.provider)) from e
            if e.status_code == 429:
                raise IARateLimitError(
                    f"Límite de uso del proveedor ({self.provider}). Espera unos minutos o revisa tu plan."
                ) from e
            raise RuntimeError(f"Error del proveedor {self.provider} ({e.status_code}): {e.message}") from e
        except openai.APIConnectionError as e:
            raise RuntimeError(f"No se pudo conectar al proveedor {self.provider}: {e.message}") from e
        except anthropic.AuthenticationError as e:
            raise IAAuthError(
                "Anthropic rechazó la API Key (401). Revisa la clave en console.anthropic.com y «Configurar IA»."
            ) from e
        except anthropic.APIStatusError as e:
            if getattr(e, "status_code", None) == 401:
                raise IAAuthError(
                    "Anthropic rechazó la autenticación (401). Actualiza la API Key en «Configurar IA»."
                ) from e
            if getattr(e, "status_code", None) == 429:
                raise IARateLimitError("Límite de uso en Anthropic. Espera o revisa tu plan.") from e
            raise RuntimeError(f"Error Anthropic: {getattr(e, 'message', str(e))}") from e

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
