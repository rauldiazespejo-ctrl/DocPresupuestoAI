# DocPresupuestoAI 🏗️🤖

## El mejor software de documentación y presupuestos técnicos basado en IA

---

## ¿Qué hace este software?

DocPresupuestoAI analiza automáticamente las **bases técnicas y administrativas** de tus proyectos usando Inteligencia Artificial y genera en segundos:

| Documento | Formato | Descripción |
|---|---|---|
| 📊 Presupuesto | PDF | Partidas, precios, resumen financiero profesional |
| 📈 Presupuesto | Excel | Planilla editable con fórmulas automáticas |
| 📋 Informe Técnico | PDF | Metodología, alcance, programa de trabajo |
| 🏆 Propuesta Técnica | PDF | Propuesta ganadora para licitaciones |

---

## Inicio rápido

### 1. Iniciar el sistema
```bash
chmod +x iniciar.sh && ./iniciar.sh
```

### 2. Configurar API Key
- Abre la interfaz en `frontend/index.html`
- Haz clic en **"Configurar IA"**
- Ingresa tu API Key de **OpenAI** o **Anthropic**

### 3. Crear un proyecto
- Haz clic en **"Nuevo Proyecto"**
- Arrastra el documento PDF/DOCX con las bases técnicas
- Ingresa **Código OT / Licitación** obligatorio con formato `OT_XXXXXXXX_CLIENTE`
- El sistema analiza automáticamente con IA

### 4. Generar documentos
- Ve a **"Generar Documentos"**
- Selecciona el tipo de documento
- Haz clic en **"Generar con IA"**
- ¡Descarga el resultado en segundos!

---

## Formatos de entrada soportados

- ✅ **PDF** — Bases técnicas y administrativas
- ✅ **DOCX/DOC** — Documentos Word
- ✅ **XLSX/XLS** — Planillas Excel
- ✅ **TXT** — Texto plano

---

## Estructura del proyecto

```
DocPresupuestoAI/
├── backend/
│   ├── main.py          # API FastAPI
│   ├── ai_engine.py     # Motor de IA (OpenAI/Anthropic)
│   ├── ai_prompts.py    # Prompts especializados
│   ├── extractor.py     # Extracción de texto
│   └── generator.py     # Generador PDF/Excel
├── database/
│   └── models.py        # Base de datos SQLite
├── frontend/
│   └── index.html       # Interfaz web completa
├── uploads/             # Documentos subidos
├── exports/             # Documentos generados
└── iniciar.sh           # Script de inicio
```

---

## Tecnologías

- **Backend**: FastAPI + Python 3
- **IA**: OpenAI GPT-4o / Anthropic Claude 3.5
- **PDF**: ReportLab (diseño profesional)
- **Excel**: OpenPyXL
- **BD**: SQLite
- **Frontend**: HTML5/CSS3/JS puro (sin dependencias)
- **Extracción**: pdfplumber, python-docx

---

## API Endpoints

| Método | Endpoint | Descripción |
|---|---|---|
| POST | `/api/subir-documento` | Sube y analiza documento |
| GET | `/api/proyectos` | Lista proyectos |
| POST | `/api/generar-documento` | Genera documento |
| GET | `/api/descargar/{id}` | Descarga documento |
| POST | `/api/consulta` | Chat con IA sobre el proyecto |
| POST | `/api/requisitos/sincronizar/{proyecto_id}` | Sincroniza requisitos desde datos extraídos por IA |
| GET | `/api/proyectos/{id}/requisitos` | Lista requisitos documentales del proyecto |
| POST | `/api/requisitos` | Crea requisito documental manual |
| PUT | `/api/requisitos/{id}` | Actualiza estado y observaciones del requisito |
| POST | `/api/requisitos/{id}/evidencia` | Sube evidencia documental ordenada por carpeta de requisito |
| GET | `/api/requisitos/{id}/evidencias` | Lista evidencias de un requisito |
| GET | `/api/evidencias/{id}/descargar` | Descarga evidencia documental |
| GET | `/api/proyectos/{id}/documentacion/arbol` | Estructura documental por categoría/carpeta/requisito |
| POST | `/api/proyectos/{id}/documentacion/exportar?formato=excel|pdf` | Exporta índice documental respetando orden 1_ANT...6_ANT |
| POST | `/api/prediccion/oferta` | Registra oferta para predicción |
| POST | `/api/prediccion/calcular/{oferta_id}` | Calcula probabilidad de adjudicación |
| POST | `/api/prediccion/simular` | Simula hasta 3 escenarios de adjudicación |
| POST | `/api/prediccion/bid-leveling` | Compara 2+ ofertas y recomienda ranking ajustado por riesgo |
| POST | `/api/prediccion/atractividad` | Evalúa atractividad Go/No-Go usando histórico de 3 años |
| POST | `/api/prediccion/atractividad/ml/train` | Entrena modelo ML v2 con histórico 3 años |
| GET | `/api/prediccion/atractividad/ml/status` | Estado y métricas del modelo ML v2 |
| POST | `/api/prediccion/atractividad/ml/evaluar` | Evalúa atractividad con modelo ML v2 entrenado |
| GET | `/api/proyectos/{id}/ofertas` | Lista ofertas de un proyecto |
| GET | `/api/proyectos/{id}/predicciones` | Historial de predicciones del proyecto |
| POST | `/api/historico-licitaciones` | Registra licitación histórica adjudicada/no adjudicada |
| POST | `/api/historico-licitaciones/importar` | Importa histórico masivo desde CSV/XLSX |
| GET | `/api/historico-licitaciones?ultimos_anios=3` | Lista histórico para modelo de atractividad |

Plantilla sugerida para importación masiva:
- `templates/plantilla_historico_licitaciones.xlsx`

---

## Orden documental (estructura tipo licitación)

El módulo de documentación requerida organiza los requisitos y evidencias en el mismo orden de carpetas de referencia:

- `1_ANT. ECO`
- `2_ANT. ADJ`
- `3_ANT. TEC`
- `4_ANT. PREV`
- `5_ANT. ADM`
- `6_ANT. FACT`

Ruta base por proyecto:

- `uploads/proyecto_<id>/documentacion_requerida/<seccion>/<requisito_slug>/`

El índice documental exportado incluye formato tipo dossier:
- Portada con datos de proyecto/cliente/fecha
- Resumen ejecutivo de cumplimiento por sección
- Detalle completo de requisitos y evidencias

## Desarrollado con ❤️ usando Blackbox AI
