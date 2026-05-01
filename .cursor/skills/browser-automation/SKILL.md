---
name: browser-automation
description: Skill para automatizacion de navegador en DocPresupuestoAI. Permite probar UI, completar flujos y validar comportamiento visual y funcional.
---

# Browser Automation - DocPresupuestoAI

Usa esta skill para validar la experiencia de usuario y automatizar pruebas de interfaz.

## Objetivo

Ejecutar pruebas repetibles del frontend y flujos end-to-end con evidencia clara.

## Casos de uso

- Probar flujo completo: crear proyecto, subir bases, generar documento y descargar
- Verificar mensajes de error y estados vacios
- Capturar evidencia visual en checkpoints clave
- Validar compatibilidad basica de resolucion y comportamiento UI

## Reglas practicas

- Priorizar rutas criticas de negocio sobre pruebas cosmeticas
- Mantener pasos deterministas y datos de prueba conocidos
- Reportar fallos con contexto (paso, resultado esperado, resultado real)

## Entregable

- Resultado de ejecucion por escenario
- Evidencia de fallos y reproduccion
- Recomendaciones concretas para correccion
