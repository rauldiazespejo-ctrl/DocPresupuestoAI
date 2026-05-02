# Protocolo de Validacion P1 - DocPresupuestoAI

Fecha: ____ / ____ / ______

Proyecto piloto: ______________________

Responsable general: __________________

## 1) Objetivo

Validar operativamente el flujo completo de licitaciones:

- Ingreso de BBTT/BBAA
- Extraccion y estructuracion documental
- Generacion de dossier
- Prediccion, bid leveling y atractividad Go/No-Go con historico y ML v2

## 2) Roles sugeridos

- Lider Estudios y Propuestas: decide aprobacion final
- Analista Tecnico: revisa extraccion, requisitos y metodologia
- Analista Comercial: revisa presupuesto, ofertas y bid leveling
- Analista HSE/Compliance: valida documental y evidencias por requisito

## 3) Evidencias minimas a adjuntar

- Captura de `health` OK
- Captura de configuracion IA activa
- Captura de proyecto creado con codigo OT valido
- Captura de explorador documental 1_ANT...6_ANT
- Archivo de evidencia subido por requisito
- Exportacion de dossier (PDF o Excel)
- Resultado de prediccion y bid leveling
- Resultado de atractividad (heuristica y ML v2)

## 4) Matriz de ejecucion

Estado permitido: Pendiente | En curso | Aprobado | Rechazado

| ID | Caso de prueba | Responsable | Evidencia | Estado | Observaciones |
|---|---|---|---|---|---|
| A1 | Backend inicia con `./iniciar.sh` o `./desktop/ejecutar_desktop.sh` |  |  |  |  |
| A2 | `GET /health` responde `status=ok` |  |  |  |  |
| A3 | Frontend carga sin error critico |  |  |  |  |
| B1 | Configuracion IA guardada y visible en UI |  |  |  |  |
| C1 | Valida codigo OT obligatorio |  |  |  |  |
| C2 | Valida formato `OT_XXXXXXXX_CLIENTE` |  |  |  |  |
| C3 | Autodeteccion de codigo OT desde archivo/carpeta |  |  |  |  |
| C4 | Proyecto creado desde BBTT/BBAA con datos extraidos |  |  |  |  |
| D1 | Sincroniza requisitos desde IA sin duplicados |  |  |  |  |
| D2 | Orden documental visible `1_ANT` a `6_ANT` |  |  |  |  |
| D3 | Subida de evidencia por requisito exitosa |  |  |  |  |
| D4 | Cambio de estado requisito (pendiente/revision/cumplido) |  |  |  |  |
| E1 | Exporta indice documental Excel |  |  |  |  |
| E2 | Exporta indice documental PDF (dossier) |  |  |  |  |
| F1 | Registro de oferta exitoso |  |  |  |  |
| F2 | Prediccion risk-aware completa |  |  |  |  |
| F3 | Simulador de escenarios operativo |  |  |  |  |
| F4 | Bid leveling con 2+ ofertas y recomendacion |  |  |  |  |
| G1 | Descarga plantilla historico |  |  |  |  |
| G2 | Importacion masiva CSV/XLSX |  |  |  |  |
| G3 | Atractividad Go/No-Go heuristica |  |  |  |  |
| G4 | Entrenamiento ML v2 completado |  |  |  |  |
| G5 | Estado ML reporta `ready=true` |  |  |  |  |
| G6 | Evaluacion atractividad ML v2 operativa |  |  |  |  |

## 5) Criterio de aprobacion P1

Para aprobar P1 deben quedar en `Aprobado` al menos:

- A1, B1, C4
- D2, D3
- E1 o E2
- F2, F4
- G2, G4, G6

## 6) Registro de incidencias

| N° | Fecha | Severidad (Alta/Media/Baja) | Incidencia | Causa probable | Accion correctiva | Responsable | Estado |
|---|---|---|---|---|---|---|---|
| 1 |  |  |  |  |  |  |  |
| 2 |  |  |  |  |  |  |  |
| 3 |  |  |  |  |  |  |  |

## 7) Acta de cierre

- Resultado final: Aprobado / Rechazado
- Fecha cierre: ____ / ____ / ______
- Observaciones finales:

____________________________________________________________________

____________________________________________________________________

Firmas:

- Lider Estudios y Propuestas: ______________________
- Responsable tecnico: ______________________________
