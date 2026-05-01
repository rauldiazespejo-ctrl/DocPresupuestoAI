---
name: qa-testing
description: Skill de aseguramiento de calidad para DocPresupuestoAI. Define pruebas funcionales, de regresion y de integracion para backend, frontend y flujos de licitaciones.
---

# QA Testing - DocPresupuestoAI

Usa esta skill para validar que el sistema funcione de forma consistente antes de entregar cambios.

## Objetivo

Reducir regresiones y asegurar que los flujos criticos de licitaciones funcionen de punta a punta.

## Alcance de pruebas

- API: salud, creacion de proyecto, carga de documento, generacion, descarga y consulta
- Frontend: flujo principal de usuario y estados de error
- Datos: consistencia entre JSON extraido, registros en BD y archivos exportados
- Integracion IA: manejo de respuestas invalidas, timeouts y reintentos

## Estrategia minima

1. Smoke tests de endpoints criticos
2. Pruebas de regresion de flujos clave
3. Casos borde de entrada (documentos vacios, formato invalido, payload incompleto)
4. Verificacion de artefactos generados (PDF/Excel) y metadatos

## Criterios de salida

- Ningun flujo critico roto
- Errores manejados con mensajes claros
- Cambios documentados con pasos manuales de verificacion
