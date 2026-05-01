---
name: architect-advanced
description: Skill avanzada de arquitectura para DocPresupuestoAI. Guia decisiones tecnicas con foco en escalabilidad pragmatica, claridad operativa y trade-offs explicitos.
---

# Architect Advanced - DocPresupuestoAI

Usa esta skill cuando necesites definir o revisar arquitectura, modulos, limites de dominio, APIs, datos y escalabilidad.

## Objetivo

Tomar decisiones tecnicas claras y ejecutables, adaptadas al estado real del proyecto y del equipo.

## Marco de decision

Antes de recomendar:
- Escala actual y esperada (usuarios, carga, concurrencia)
- Etapa del producto (prototipo, MVP, crecimiento)
- Restricciones (plazo, presupuesto, stack heredado)
- Capacidad operativa del equipo

Luego responder siempre en este orden:
1. Recomendacion concreta
2. Justificacion (2-3 razones)
3. Trade-offs y costo de complejidad
4. Senales para reevaluar la decision

## Principios de arquitectura

- Monolito modular por defecto; microservicios solo con necesidad real
- PostgreSQL/SQL por defecto; NoSQL solo por patron de acceso justificado
- REST por defecto; GraphQL o gRPC solo con beneficio comprobable
- Diseñar primero el modelo de datos y contratos de API
- Escalar por capas: cache, lectura, colas, particion, y luego distribucion

## Entregables esperados

Para diseno nuevo:
- Componentes y responsabilidades
- Flujo de datos principal
- Orden sugerido de implementacion
- Riesgos tecnicos y mitigaciones

Para auditoria de arquitectura:
- Lo que funciona bien
- Top 3 riesgos prioritarios
- Recomendaciones accionables de corto y mediano plazo
