---
name: dev-advanced
description: Skill avanzada para desarrollo full-stack en DocPresupuestoAI. Implementa features end-to-end, corrige bugs, valida seguridad y deja cambios listos para ejecutar.
---

# Dev Advanced - DocPresupuestoAI

Usa esta skill para tareas de implementacion en backend, frontend, base de datos e integraciones del proyecto.

## Objetivo

Entregar cambios funcionales, mantenibles y listos para probar, con alcance controlado y enfoque practico.

## Flujo de trabajo

1. Entender el contexto
- Leer primero archivos existentes antes de proponer cambios
- Detectar stack, convenciones, patrones y limites del proyecto
- Aclarar solo lo estrictamente ambiguo

2. Definir enfoque minimo
- Proponer 2-4 pasos concretos para tareas no triviales
- Evitar sobrearquitectura y refactors innecesarios

3. Implementar
- Respetar estilo y estructura actuales
- Tocar solo los archivos necesarios
- Mantener separacion de responsabilidades (controladores delgados, logica en servicios)
- Validar entradas en bordes del sistema

4. Verificar
- Revisar casos borde y manejo de errores
- Ejecutar pruebas y chequeos disponibles
- Anotar riesgos residuales y siguientes pasos

## Principios obligatorios

- Seguridad por defecto: no exponer secretos, validar input y evitar inyecciones
- Simplicidad primero: el codigo debe ser facil de leer y mantener
- Alcance estricto: resolver el pedido, sin agregar extras no solicitados
- Compatibilidad: no romper contratos existentes sin explicitar migracion

## Checklist final

- Codigo compila y corre
- Cambios cumplen el requerimiento
- No se introducen errores de lint evidentes
- Se documenta cualquier paso manual pendiente
