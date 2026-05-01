---
name: security-audit
description: Skill de auditoria de seguridad para DocPresupuestoAI. Evalua vulnerabilidades en API, archivos, autenticacion, secretos y superficie de ataque.
---

# Security Audit - DocPresupuestoAI

Usa esta skill para revisar riesgos de seguridad antes de exponer el sistema a usuarios reales.

## Objetivo

Detectar y mitigar riesgos de seguridad en procesamiento documental, API y configuracion operativa.

## Focos prioritarios

- Gestion de secretos (API keys, tokens, variables de entorno)
- Validacion de input y sanitizacion
- Subida y descarga de archivos (tipos, tamano, path traversal, malware workflow)
- CORS, autenticacion, autorizacion y control de acceso
- Dependencias y configuraciones inseguras por defecto

## Checklist minimo

1. No guardar secretos en frontend/localStorage
2. Validar tipo y tamano de archivos subidos
3. Limitar CORS y origenes confiables
4. Proteger endpoints sensibles con auth/roles
5. Registrar eventos de seguridad y errores relevantes

## Entregable

- Lista priorizada de hallazgos: critico, alto, medio, bajo
- Recomendacion accionable por hallazgo
- Riesgo residual y plan de remediacion
