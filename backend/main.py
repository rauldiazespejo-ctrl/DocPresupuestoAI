import os
import sys
import json
import uuid
import shutil
import re
import csv
import io
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import openpyxl

# Agregar paths
sys.path.insert(0, "/Users/rauldiaz/DocPresupuestoAI")

from database.models import (
    create_tables,
    get_db,
    Proyecto,
    Documento,
    ItemPresupuesto,
    OfertaLicitacion,
    PrediccionAdjudicacion,
    RequisitoDocumental,
    EvidenciaRequisito,
    HistoricoLicitacion,
)
from backend.extractor import extract_text
from backend.ai_engine import AIEngine
from backend.generator import (
    generar_presupuesto_pdf,
    generar_presupuesto_excel,
    generar_informe_pdf,
    generar_indice_documental_excel,
    generar_indice_documental_pdf,
)
from backend.adjudicacion import calcular_prediccion, calcular_atractividad_licitacion
from backend.ml_atractividad import train_logistic_model, predict_atractividad_ml

# ─── Inicialización ────────────────────────────────────────────────────────────
app = FastAPI(
    title="DocPresupuestoAI",
    description="Sistema inteligente de documentación y presupuestos basado en IA",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path("/Users/rauldiaz/DocPresupuestoAI")
UPLOADS_DIR = BASE_DIR / "uploads"
EXPORTS_DIR = BASE_DIR / "exports"
UPLOADS_DIR.mkdir(exist_ok=True)
EXPORTS_DIR.mkdir(exist_ok=True)

create_tables()

SECCIONES_DOCUMENTALES = [
    ("1_ANT. ECO", "economico"),
    ("2_ANT. ADJ", "adjudicacion"),
    ("3_ANT. TEC", "tecnico"),
    ("4_ANT. PREV", "prevencion"),
    ("5_ANT. ADM", "administrativo"),
    ("6_ANT. FACT", "facturacion"),
]
CODIGO_LICITACION_REGEX = re.compile(r"^OT_[0-9]{8}_[A-Z0-9]+(?:_[A-Z0-9]+)*$")


def _slugify(texto: str) -> str:
    limpio = re.sub(r"[^a-zA-Z0-9]+", "_", (texto or "").strip().lower())
    return limpio.strip("_")[:80] or "item"


def _normalizar_codigo_licitacion(codigo: str) -> str:
    return (codigo or "").strip().upper()


def _seccion_documental_por_categoria(categoria: str) -> str:
    cat = (categoria or "").strip().lower()
    if cat in {"economico", "econ", "presupuesto"}:
        return "1_ANT. ECO"
    if cat in {"legal", "adjudicacion", "contrato"}:
        return "2_ANT. ADJ"
    if cat in {"tecnico", "tecnica", "tecnica_operativa"}:
        return "3_ANT. TEC"
    if cat in {"hse", "prevencion", "seguridad"}:
        return "4_ANT. PREV"
    if cat in {"administrativo", "adm"}:
        return "5_ANT. ADM"
    if cat in {"facturacion", "fact", "finanzas"}:
        return "6_ANT. FACT"
    return "5_ANT. ADM"


def _carpeta_requisito(proyecto_id: int, categoria: str, nombre_requisito: str) -> Path:
    seccion = _seccion_documental_por_categoria(categoria)
    return (
        UPLOADS_DIR
        / f"proyecto_{proyecto_id}"
        / "documentacion_requerida"
        / seccion
        / _slugify(nombre_requisito)
    )

# ─── Modelos Pydantic ──────────────────────────────────────────────────────────
class ConfigIA(BaseModel):
    provider: str = "openai"
    api_key: str
    model: str = ""

class GenerarDocumentoRequest(BaseModel):
    proyecto_id: int
    tipo: str  # presupuesto_pdf, presupuesto_excel, informe_pdf, propuesta_pdf
    config_ia: ConfigIA

class ConsultaRequest(BaseModel):
    proyecto_id: int
    pregunta: str
    config_ia: ConfigIA


class OfertaLicitacionRequest(BaseModel):
    proyecto_id: int
    nombre: str
    monto_oferta: float = 0.0
    plazo_dias: int = 0
    factores: dict = Field(default_factory=dict)
    notas: str = ""


class SimulacionEscenario(BaseModel):
    nombre: str
    factores: dict = Field(default_factory=dict)


class SimularPrediccionRequest(BaseModel):
    proyecto_id: int
    escenarios: list[SimulacionEscenario] = Field(default_factory=list)


class BidLevelingRequest(BaseModel):
    proyecto_id: int
    oferta_ids: list[int] = Field(default_factory=list)


class HistoricoLicitacionRequest(BaseModel):
    codigo_licitacion: str = ""
    cliente: str
    rubro: str = ""
    monto_ofertado: float = 0.0
    margen_pct: float = 0.0
    fue_adjudicada: bool = False
    fecha_cierre: str = ""
    observaciones: str = ""


class AtractividadRequest(BaseModel):
    proyecto_id: int
    factores: dict = Field(default_factory=dict)


class TrainMLAtractividadRequest(BaseModel):
    ultimos_anios: int = 3
    epochs: int = 800
    lr: float = 0.02


class AtractividadMLV2Request(BaseModel):
    proyecto_id: int
    monto_oferta: float = 0.0
    margen_pct: float = 0.0
    rubro: str = ""
    cliente: str = ""


class RequisitoDocumentalRequest(BaseModel):
    proyecto_id: int
    nombre: str
    categoria: str = "administrativo"
    estado: str = "pendiente"
    observaciones: str = ""


class RequisitoDocumentalUpdateRequest(BaseModel):
    estado: str = "pendiente"
    observaciones: str = ""

# ─── Configuración IA en memoria (sesión) ─────────────────────────────────────
ia_config = {}
ML_DIR = EXPORTS_DIR / "ml"
ML_DIR.mkdir(exist_ok=True)
ML_ATRACTIVIDAD_MODEL_PATH = ML_DIR / "atractividad_ml_v2.json"


def _norm_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower()).strip("_")


def _to_float(v, default=0.0) -> float:
    if v is None:
        return default
    s = str(v).strip().replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        try:
            return float(v)
        except Exception:
            return default


def _to_bool(v) -> bool:
    s = str(v or "").strip().lower()
    return s in {"1", "true", "si", "sí", "yes", "y", "adjudicada", "ganada", "win"}


def _to_date(v):
    if v is None or str(v).strip() == "":
        return datetime.utcnow()
    if isinstance(v, datetime):
        return v
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return datetime.utcnow()

# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    return {"message": "DocPresupuestoAI API v1.0", "status": "online"}

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

# ─── CONFIGURACIÓN IA ─────────────────────────────────────────────────────────
@app.post("/api/config-ia")
async def configurar_ia(config: ConfigIA):
    global ia_config
    ia_config = config.dict()
    return {"message": "Configuración de IA guardada", "provider": config.provider, "model": config.model}

@app.get("/api/config-ia")
async def obtener_config_ia():
    if ia_config:
        return {"configurado": True, "provider": ia_config.get("provider"), "model": ia_config.get("model")}
    return {"configurado": False}

# ─── PROYECTOS ────────────────────────────────────────────────────────────────
@app.get("/api/proyectos")
async def listar_proyectos(db: Session = Depends(get_db)):
    proyectos = db.query(Proyecto).order_by(Proyecto.fecha_creacion.desc()).all()
    return [{
        "id": p.id,
        "nombre": p.nombre,
        "codigo_licitacion": p.codigo_licitacion or "",
        "cliente": p.cliente,
        "estado": p.estado,
        "fecha_creacion": p.fecha_creacion.isoformat() if p.fecha_creacion else "",
        "tiene_datos": bool(p.datos_extraidos)
    } for p in proyectos]

@app.get("/api/proyectos/{proyecto_id}")
async def obtener_proyecto(proyecto_id: int, db: Session = Depends(get_db)):
    proyecto = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return {
        "id": proyecto.id,
        "nombre": proyecto.nombre,
        "codigo_licitacion": proyecto.codigo_licitacion or "",
        "cliente": proyecto.cliente,
        "descripcion": proyecto.descripcion,
        "estado": proyecto.estado,
        "datos_extraidos": proyecto.datos_extraidos,
        "fecha_creacion": proyecto.fecha_creacion.isoformat() if proyecto.fecha_creacion else ""
    }

@app.delete("/api/proyectos/{proyecto_id}")
async def eliminar_proyecto(proyecto_id: int, db: Session = Depends(get_db)):
    proyecto = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    db.delete(proyecto)
    db.commit()
    return {"message": "Proyecto eliminado"}

# ─── SUBIR DOCUMENTO BASE ─────────────────────────────────────────────────────
@app.post("/api/subir-documento")
async def subir_documento(
    file: UploadFile = File(...),
    nombre_proyecto: str = Form(...),
    codigo_licitacion: str = Form(...),
    cliente: str = Form(default=""),
    provider: str = Form(default="openai"),
    api_key: str = Form(...),
    model: str = Form(default=""),
    db: Session = Depends(get_db)
):
    codigo_normalizado = _normalizar_codigo_licitacion(codigo_licitacion)
    if not CODIGO_LICITACION_REGEX.match(codigo_normalizado):
        raise HTTPException(
            status_code=400,
            detail="Codigo OT/Licitacion invalido. Usa formato OT_XXXXXXXX_CLIENTE (ej: OT_25086007_POLPAICO)",
        )

    # Guardar archivo
    ext = Path(file.filename).suffix
    filename = f"{uuid.uuid4()}{ext}"
    file_path = UPLOADS_DIR / filename
    
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    # Extraer texto
    try:
        texto = extract_text(str(file_path))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al procesar archivo: {str(e)}")
    
    if not texto.strip():
        raise HTTPException(status_code=400, detail="No se pudo extraer texto del documento")
    
    # Analizar con IA
    try:
        engine = AIEngine(provider=provider, api_key=api_key, model=model)
        datos_extraidos = engine.analizar_bases(texto)
    except Exception as e:
        datos_extraidos = {"error": str(e), "texto_raw": texto[:2000]}
    
    # Guardar en BD
    proyecto = Proyecto(
        nombre=nombre_proyecto,
        codigo_licitacion=codigo_normalizado,
        cliente=cliente,
        descripcion=datos_extraidos.get("proyecto", {}).get("descripcion", ""),
        archivo_base=str(file_path),
        datos_extraidos=datos_extraidos
    )
    db.add(proyecto)
    db.commit()
    db.refresh(proyecto)
    
    return {
        "proyecto_id": proyecto.id,
        "nombre": proyecto.nombre,
        "datos_extraidos": datos_extraidos,
        "texto_extraido_chars": len(texto),
        "message": "Documento analizado exitosamente"
    }

# ─── GENERAR DOCUMENTOS ───────────────────────────────────────────────────────
@app.post("/api/generar-documento")
async def generar_documento(req: GenerarDocumentoRequest, db: Session = Depends(get_db)):
    proyecto = db.query(Proyecto).filter(Proyecto.id == req.proyecto_id).first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    datos_extraidos = proyecto.datos_extraidos or {}
    
    # Leer texto original
    texto_bases = ""
    if proyecto.archivo_base and Path(proyecto.archivo_base).exists():
        try:
            texto_bases = extract_text(proyecto.archivo_base)
        except:
            texto_bases = ""
    
    engine = AIEngine(
        provider=req.config_ia.provider,
        api_key=req.config_ia.api_key,
        model=req.config_ia.model
    )
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_safe = proyecto.nombre.replace(" ", "_")[:30]
    
    output_path = ""
    contenido = ""
    
    try:
        if req.tipo == "presupuesto_pdf":
            datos_ppto = engine.generar_presupuesto(datos_extraidos, texto_bases)
            filename = f"Presupuesto_{nombre_safe}_{timestamp}.pdf"
            output_path = str(EXPORTS_DIR / filename)
            generar_presupuesto_pdf(datos_ppto, output_path)
            contenido = json.dumps(datos_ppto)
            
        elif req.tipo == "presupuesto_excel":
            datos_ppto = engine.generar_presupuesto(datos_extraidos, texto_bases)
            filename = f"Presupuesto_{nombre_safe}_{timestamp}.xlsx"
            output_path = str(EXPORTS_DIR / filename)
            generar_presupuesto_excel(datos_ppto, output_path)
            contenido = json.dumps(datos_ppto)
            
        elif req.tipo == "informe_pdf":
            informe_md = engine.generar_informe_tecnico(datos_extraidos, texto_bases)
            filename = f"Informe_Tecnico_{nombre_safe}_{timestamp}.pdf"
            output_path = str(EXPORTS_DIR / filename)
            generar_informe_pdf(informe_md, datos_extraidos, output_path)
            contenido = informe_md
            
        elif req.tipo == "propuesta_pdf":
            propuesta_md = engine.generar_propuesta_tecnica(datos_extraidos, texto_bases)
            filename = f"Propuesta_Tecnica_{nombre_safe}_{timestamp}.pdf"
            output_path = str(EXPORTS_DIR / filename)
            generar_informe_pdf(propuesta_md, datos_extraidos, output_path)
            contenido = propuesta_md
        
        else:
            raise HTTPException(status_code=400, detail=f"Tipo de documento no válido: {req.tipo}")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando documento: {str(e)}")
    
    # Guardar en BD
    doc = Documento(
        proyecto_id=proyecto.id,
        tipo=req.tipo,
        nombre=filename,
        contenido=contenido[:5000],
        archivo_generado=output_path
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    return {
        "documento_id": doc.id,
        "filename": filename,
        "tipo": req.tipo,
        "download_url": f"/api/descargar/{doc.id}",
        "message": "Documento generado exitosamente"
    }

# ─── DESCARGAR DOCUMENTO ──────────────────────────────────────────────────────
@app.get("/api/descargar/{documento_id}")
async def descargar_documento(documento_id: int, db: Session = Depends(get_db)):
    doc = db.query(Documento).filter(Documento.id == documento_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    if not Path(doc.archivo_generado).exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado en disco")
    
    return FileResponse(
        path=doc.archivo_generado,
        filename=doc.nombre,
        media_type="application/octet-stream"
    )

# ─── LISTAR DOCUMENTOS DE PROYECTO ───────────────────────────────────────────
@app.get("/api/proyectos/{proyecto_id}/documentos")
async def listar_documentos(proyecto_id: int, db: Session = Depends(get_db)):
    docs = db.query(Documento).filter(Documento.proyecto_id == proyecto_id).all()
    return [{
        "id": d.id,
        "tipo": d.tipo,
        "nombre": d.nombre,
        "fecha_creacion": d.fecha_creacion.isoformat() if d.fecha_creacion else "",
        "download_url": f"/api/descargar/{d.id}"
    } for d in docs]

# ─── CONSULTA LIBRE ───────────────────────────────────────────────────────────
@app.post("/api/consulta")
async def consulta_libre(req: ConsultaRequest, db: Session = Depends(get_db)):
    proyecto = db.query(Proyecto).filter(Proyecto.id == req.proyecto_id).first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    contexto = json.dumps(proyecto.datos_extraidos or {}, ensure_ascii=False)
    
    try:
        engine = AIEngine(
            provider=req.config_ia.provider,
            api_key=req.config_ia.api_key,
            model=req.config_ia.model
        )
        respuesta = engine.consulta_libre(req.pregunta, contexto)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return {"respuesta": respuesta, "pregunta": req.pregunta}

# ─── DATOS EXTRAÍDOS ─────────────────────────────────────────────────────────
@app.get("/api/proyectos/{proyecto_id}/datos")
async def obtener_datos_extraidos(proyecto_id: int, db: Session = Depends(get_db)):
    proyecto = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    return proyecto.datos_extraidos or {}

@app.put("/api/proyectos/{proyecto_id}/datos")
async def actualizar_datos(proyecto_id: int, datos: dict, db: Session = Depends(get_db)):
    proyecto = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    proyecto.datos_extraidos = datos
    proyecto.fecha_actualizacion = datetime.utcnow()
    db.commit()
    return {"message": "Datos actualizados"}


# ─── DOCUMENTACION REQUERIDA ──────────────────────────────────────────────────
@app.post("/api/requisitos/sincronizar/{proyecto_id}")
async def sincronizar_requisitos_desde_ia(proyecto_id: int, db: Session = Depends(get_db)):
    proyecto = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    datos = proyecto.datos_extraidos or {}
    candidatos = []
    candidatos += [("administrativo", x) for x in (datos.get("requisitos_administrativos") or [])]
    candidatos += [("tecnico", x) for x in (datos.get("requisitos_tecnicos") or [])]
    candidatos += [("administrativo", x) for x in (datos.get("documentos_requeridos") or [])]

    creados = 0
    for categoria, nombre in candidatos:
        nombre_limpio = str(nombre).strip()
        if not nombre_limpio:
            continue
        existente = (
            db.query(RequisitoDocumental)
            .filter(
                RequisitoDocumental.proyecto_id == proyecto_id,
                RequisitoDocumental.nombre == nombre_limpio,
            )
            .first()
        )
        if existente:
            continue
        nuevo = RequisitoDocumental(
            proyecto_id=proyecto_id,
            nombre=nombre_limpio,
            categoria=categoria,
            estado="pendiente",
            fuente="ia",
        )
        db.add(nuevo)
        creados += 1

    db.commit()
    return {"message": "Requisitos sincronizados", "creados": creados}


@app.get("/api/proyectos/{proyecto_id}/requisitos")
async def listar_requisitos_documentales(proyecto_id: int, db: Session = Depends(get_db)):
    requisitos = (
        db.query(RequisitoDocumental)
        .filter(RequisitoDocumental.proyecto_id == proyecto_id)
        .order_by(RequisitoDocumental.fecha_creacion.desc())
        .all()
    )
    evidencias = (
        db.query(EvidenciaRequisito)
        .filter(EvidenciaRequisito.proyecto_id == proyecto_id)
        .all()
    )
    conteo_evidencias = {}
    for e in evidencias:
        conteo_evidencias[e.requisito_id] = conteo_evidencias.get(e.requisito_id, 0) + 1

    return [
        {
            "id": r.id,
            "proyecto_id": r.proyecto_id,
            "nombre": r.nombre,
            "categoria": r.categoria,
            "seccion": _seccion_documental_por_categoria(r.categoria),
            "estado": r.estado,
            "observaciones": r.observaciones or "",
            "fuente": r.fuente or "manual",
            "carpeta_objetivo": str(_carpeta_requisito(r.proyecto_id, r.categoria, r.nombre).relative_to(BASE_DIR)),
            "evidencias_count": conteo_evidencias.get(r.id, 0),
            "fecha_creacion": r.fecha_creacion.isoformat() if r.fecha_creacion else "",
            "fecha_actualizacion": r.fecha_actualizacion.isoformat() if r.fecha_actualizacion else "",
        }
        for r in requisitos
    ]


@app.post("/api/requisitos")
async def crear_requisito_documental(req: RequisitoDocumentalRequest, db: Session = Depends(get_db)):
    proyecto = db.query(Proyecto).filter(Proyecto.id == req.proyecto_id).first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    if not req.nombre.strip():
        raise HTTPException(status_code=400, detail="Nombre de requisito es obligatorio")

    requisito = RequisitoDocumental(
        proyecto_id=req.proyecto_id,
        nombre=req.nombre.strip(),
        categoria=req.categoria or "administrativo",
        estado=req.estado or "pendiente",
        observaciones=req.observaciones or "",
        fuente="manual",
        fecha_actualizacion=datetime.utcnow(),
    )
    db.add(requisito)
    db.commit()
    db.refresh(requisito)
    return {"id": requisito.id, "message": "Requisito creado"}


@app.put("/api/requisitos/{requisito_id}")
async def actualizar_requisito_documental(
    requisito_id: int, req: RequisitoDocumentalUpdateRequest, db: Session = Depends(get_db)
):
    requisito = db.query(RequisitoDocumental).filter(RequisitoDocumental.id == requisito_id).first()
    if not requisito:
        raise HTTPException(status_code=404, detail="Requisito no encontrado")

    requisito.estado = req.estado or requisito.estado
    requisito.observaciones = req.observaciones or ""
    requisito.fecha_actualizacion = datetime.utcnow()
    db.commit()

    return {"message": "Requisito actualizado", "id": requisito.id}


@app.post("/api/requisitos/{requisito_id}/evidencia")
async def subir_evidencia_requisito(requisito_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    requisito = db.query(RequisitoDocumental).filter(RequisitoDocumental.id == requisito_id).first()
    if not requisito:
        raise HTTPException(status_code=404, detail="Requisito no encontrado")

    ext = Path(file.filename or "").suffix.lower()
    nombre_limpio = Path(file.filename or "").name or f"evidencia_{uuid.uuid4().hex[:8]}"
    carpeta = _carpeta_requisito(requisito.proyecto_id, requisito.categoria, requisito.nombre)
    carpeta.mkdir(parents=True, exist_ok=True)

    nombre_guardado = f"{uuid.uuid4().hex}_{nombre_limpio}"
    destino = carpeta / nombre_guardado
    with open(destino, "wb") as f:
        shutil.copyfileobj(file.file, f)

    ultimo_orden = (
        db.query(EvidenciaRequisito)
        .filter(EvidenciaRequisito.requisito_id == requisito_id)
        .order_by(EvidenciaRequisito.orden.desc())
        .first()
    )
    siguiente_orden = (ultimo_orden.orden + 1) if ultimo_orden else 1

    evidencia = EvidenciaRequisito(
        proyecto_id=requisito.proyecto_id,
        requisito_id=requisito.id,
        nombre_archivo=nombre_limpio,
        extension=ext,
        archivo_path=str(destino),
        carpeta_relativa=str(carpeta.relative_to(BASE_DIR)),
        orden=siguiente_orden,
    )
    db.add(evidencia)

    if requisito.estado == "pendiente":
        requisito.estado = "en_revision"
        requisito.fecha_actualizacion = datetime.utcnow()

    db.commit()
    db.refresh(evidencia)

    return {
        "id": evidencia.id,
        "requisito_id": evidencia.requisito_id,
        "nombre_archivo": evidencia.nombre_archivo,
        "carpeta_relativa": evidencia.carpeta_relativa,
        "orden": evidencia.orden,
        "message": "Evidencia subida",
    }


@app.get("/api/requisitos/{requisito_id}/evidencias")
async def listar_evidencias_requisito(requisito_id: int, db: Session = Depends(get_db)):
    evidencias = (
        db.query(EvidenciaRequisito)
        .filter(EvidenciaRequisito.requisito_id == requisito_id)
        .order_by(EvidenciaRequisito.orden.asc(), EvidenciaRequisito.fecha_creacion.asc())
        .all()
    )
    return [
        {
            "id": e.id,
            "requisito_id": e.requisito_id,
            "nombre_archivo": e.nombre_archivo,
            "extension": e.extension,
            "carpeta_relativa": e.carpeta_relativa,
            "orden": e.orden,
            "download_url": f"/api/evidencias/{e.id}/descargar",
            "fecha_creacion": e.fecha_creacion.isoformat() if e.fecha_creacion else "",
        }
        for e in evidencias
    ]


@app.get("/api/evidencias/{evidencia_id}/descargar")
async def descargar_evidencia(evidencia_id: int, db: Session = Depends(get_db)):
    evidencia = db.query(EvidenciaRequisito).filter(EvidenciaRequisito.id == evidencia_id).first()
    if not evidencia:
        raise HTTPException(status_code=404, detail="Evidencia no encontrada")
    if not Path(evidencia.archivo_path).exists():
        raise HTTPException(status_code=404, detail="Archivo de evidencia no encontrado")
    return FileResponse(
        path=evidencia.archivo_path,
        filename=evidencia.nombre_archivo,
        media_type="application/octet-stream",
    )


@app.get("/api/proyectos/{proyecto_id}/documentacion/arbol")
async def obtener_arbol_documentacion(proyecto_id: int, db: Session = Depends(get_db)):
    requisitos = (
        db.query(RequisitoDocumental)
        .filter(RequisitoDocumental.proyecto_id == proyecto_id)
        .order_by(RequisitoDocumental.categoria.asc(), RequisitoDocumental.nombre.asc())
        .all()
    )
    evidencias = (
        db.query(EvidenciaRequisito)
        .filter(EvidenciaRequisito.proyecto_id == proyecto_id)
        .order_by(EvidenciaRequisito.carpeta_relativa.asc(), EvidenciaRequisito.orden.asc())
        .all()
    )

    evidencias_por_req = {}
    for e in evidencias:
        evidencias_por_req.setdefault(e.requisito_id, []).append({
            "id": e.id,
            "nombre_archivo": e.nombre_archivo,
            "orden": e.orden,
            "carpeta_relativa": e.carpeta_relativa,
            "download_url": f"/api/evidencias/{e.id}/descargar",
        })

    secciones = {
        codigo: {"seccion": codigo, "categoria_base": categoria, "requisitos": []}
        for codigo, categoria in SECCIONES_DOCUMENTALES
    }

    for r in requisitos:
        seccion = _seccion_documental_por_categoria(r.categoria)
        secciones.setdefault(seccion, {"seccion": seccion, "categoria_base": "administrativo", "requisitos": []})
        secciones[seccion]["requisitos"].append({
            "requisito_id": r.id,
            "requisito": r.nombre,
            "categoria": r.categoria,
            "estado": r.estado,
            "carpeta_objetivo": str(_carpeta_requisito(r.proyecto_id, r.categoria, r.nombre).relative_to(BASE_DIR)),
            "evidencias": evidencias_por_req.get(r.id, []),
        })

    return {
        "proyecto_id": proyecto_id,
        "secciones": [secciones[codigo] for codigo, _ in SECCIONES_DOCUMENTALES],
    }


@app.post("/api/proyectos/{proyecto_id}/documentacion/exportar")
async def exportar_indice_documental(proyecto_id: int, formato: str = "excel", db: Session = Depends(get_db)):
    proyecto = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    requisitos = (
        db.query(RequisitoDocumental)
        .filter(RequisitoDocumental.proyecto_id == proyecto_id)
        .order_by(RequisitoDocumental.categoria.asc(), RequisitoDocumental.nombre.asc())
        .all()
    )
    evidencias = (
        db.query(EvidenciaRequisito)
        .filter(EvidenciaRequisito.proyecto_id == proyecto_id)
        .order_by(EvidenciaRequisito.carpeta_relativa.asc(), EvidenciaRequisito.orden.asc())
        .all()
    )

    evidencias_por_req = {}
    for e in evidencias:
        evidencias_por_req.setdefault(e.requisito_id, []).append({
            "nombre_archivo": e.nombre_archivo,
            "orden": e.orden,
            "carpeta_relativa": e.carpeta_relativa,
            "download_url": f"/api/evidencias/{e.id}/descargar",
        })

    secciones = {
        codigo: {"seccion": codigo, "categoria_base": categoria, "requisitos": []}
        for codigo, categoria in SECCIONES_DOCUMENTALES
    }
    for r in requisitos:
        seccion = _seccion_documental_por_categoria(r.categoria)
        secciones[seccion]["requisitos"].append({
            "requisito_id": r.id,
            "requisito": r.nombre,
            "categoria": r.categoria,
            "estado": r.estado,
            "carpeta_objetivo": str(_carpeta_requisito(r.proyecto_id, r.categoria, r.nombre).relative_to(BASE_DIR)),
            "evidencias": evidencias_por_req.get(r.id, []),
        })
    secciones_ordenadas = [secciones[codigo] for codigo, _ in SECCIONES_DOCUMENTALES]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_safe = _slugify(proyecto.nombre)[:30]
    fecha_generacion = datetime.now().strftime("%d/%m/%Y %H:%M")
    codigo_licitacion = (proyecto.codigo_licitacion or "").strip()
    logo_candidates = [
        BASE_DIR / "templates" / "logo.png",
        BASE_DIR / "templates" / "logo.jpg",
        BASE_DIR / "templates" / "logo.jpeg",
    ]
    logo_path = ""
    for candidate in logo_candidates:
        if candidate.exists():
            logo_path = str(candidate)
            break
    fmt = (formato or "excel").strip().lower()
    if fmt not in {"excel", "pdf"}:
        raise HTTPException(status_code=400, detail="Formato no valido. Usa: excel o pdf")

    if fmt == "excel":
        filename = f"Indice_Documental_{nombre_safe}_{timestamp}.xlsx"
        output_path = str(EXPORTS_DIR / filename)
        generar_indice_documental_excel(
            proyecto_nombre=proyecto.nombre,
            secciones_ordenadas=secciones_ordenadas,
            output_path=output_path,
            cliente=proyecto.cliente or "",
            fecha_generacion=fecha_generacion,
            codigo_licitacion=codigo_licitacion,
        )
        tipo_doc = "indice_documental_excel"
    else:
        filename = f"Indice_Documental_{nombre_safe}_{timestamp}.pdf"
        output_path = str(EXPORTS_DIR / filename)
        generar_indice_documental_pdf(
            proyecto_nombre=proyecto.nombre,
            secciones_ordenadas=secciones_ordenadas,
            output_path=output_path,
            cliente=proyecto.cliente or "",
            fecha_generacion=fecha_generacion,
            logo_path=logo_path,
            codigo_licitacion=codigo_licitacion,
        )
        tipo_doc = "indice_documental_pdf"

    doc = Documento(
        proyecto_id=proyecto.id,
        tipo=tipo_doc,
        nombre=filename,
        contenido="Indice documental exportado",
        datos_json={"formato": fmt},
        archivo_generado=output_path,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return {
        "documento_id": doc.id,
        "filename": filename,
        "tipo": tipo_doc,
        "download_url": f"/api/descargar/{doc.id}",
        "message": "Indice documental exportado exitosamente",
    }


# ─── PREDICCION DE ADJUDICACION ──────────────────────────────────────────────
@app.post("/api/prediccion/oferta")
async def crear_oferta_licitacion(req: OfertaLicitacionRequest, db: Session = Depends(get_db)):
    proyecto = db.query(Proyecto).filter(Proyecto.id == req.proyecto_id).first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    oferta = OfertaLicitacion(
        proyecto_id=req.proyecto_id,
        nombre=req.nombre,
        monto_oferta=req.monto_oferta,
        plazo_dias=req.plazo_dias,
        factores=req.factores or {},
        notas=req.notas,
    )
    db.add(oferta)
    db.commit()
    db.refresh(oferta)

    return {
        "oferta_id": oferta.id,
        "proyecto_id": oferta.proyecto_id,
        "nombre": oferta.nombre,
        "message": "Oferta registrada",
    }


@app.get("/api/proyectos/{proyecto_id}/ofertas")
async def listar_ofertas_proyecto(proyecto_id: int, db: Session = Depends(get_db)):
    ofertas = (
        db.query(OfertaLicitacion)
        .filter(OfertaLicitacion.proyecto_id == proyecto_id)
        .order_by(OfertaLicitacion.fecha_creacion.desc())
        .all()
    )
    return [
        {
            "id": o.id,
            "nombre": o.nombre,
            "monto_oferta": o.monto_oferta,
            "plazo_dias": o.plazo_dias,
            "factores": o.factores or {},
            "fecha_creacion": o.fecha_creacion.isoformat() if o.fecha_creacion else "",
        }
        for o in ofertas
    ]


@app.post("/api/prediccion/calcular/{oferta_id}")
async def calcular_prediccion_adjudicacion(oferta_id: int, db: Session = Depends(get_db)):
    oferta = db.query(OfertaLicitacion).filter(OfertaLicitacion.id == oferta_id).first()
    if not oferta:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")

    proyecto = db.query(Proyecto).filter(Proyecto.id == oferta.proyecto_id).first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    resultado = calcular_prediccion(proyecto.datos_extraidos or {}, oferta.factores or {})

    pred = PrediccionAdjudicacion(
        proyecto_id=proyecto.id,
        oferta_id=oferta.id,
        score=resultado["score"],
        probabilidad=resultado["probabilidad_adjudicacion"],
        resultado_json=resultado,
        version_modelo=resultado.get("version_modelo", "rules-v1"),
    )
    db.add(pred)
    db.commit()
    db.refresh(pred)

    return {
        "prediccion_id": pred.id,
        "proyecto_id": pred.proyecto_id,
        "oferta_id": pred.oferta_id,
        "resultado": resultado,
    }


@app.get("/api/proyectos/{proyecto_id}/predicciones")
async def listar_predicciones_proyecto(proyecto_id: int, db: Session = Depends(get_db)):
    predicciones = (
        db.query(PrediccionAdjudicacion)
        .filter(PrediccionAdjudicacion.proyecto_id == proyecto_id)
        .order_by(PrediccionAdjudicacion.fecha_creacion.desc())
        .all()
    )
    ofertas = (
        db.query(OfertaLicitacion)
        .filter(OfertaLicitacion.proyecto_id == proyecto_id)
        .all()
    )
    oferta_nombre_por_id = {o.id: o.nombre for o in ofertas}

    return [
        {
            "id": p.id,
            "oferta_id": p.oferta_id,
            "oferta_nombre": oferta_nombre_por_id.get(p.oferta_id, f"Oferta #{p.oferta_id}"),
            "score": p.score,
            "probabilidad": p.probabilidad,
            "version_modelo": p.version_modelo,
            "fecha_creacion": p.fecha_creacion.isoformat() if p.fecha_creacion else "",
            "resultado": p.resultado_json or {},
        }
        for p in predicciones
    ]


@app.post("/api/prediccion/simular")
async def simular_prediccion(req: SimularPrediccionRequest, db: Session = Depends(get_db)):
    proyecto = db.query(Proyecto).filter(Proyecto.id == req.proyecto_id).first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    if not req.escenarios:
        raise HTTPException(status_code=400, detail="Debes enviar al menos un escenario")

    resultados = []
    for esc in req.escenarios[:3]:
        resultado = calcular_prediccion(proyecto.datos_extraidos or {}, esc.factores or {})
        resultados.append({
            "escenario": esc.nombre,
            "resultado": resultado,
        })

    resultados = sorted(resultados, key=lambda x: x["resultado"].get("score", 0), reverse=True)

    return {
        "proyecto_id": proyecto.id,
        "total_escenarios": len(resultados),
        "ranking": resultados,
    }


@app.post("/api/historico-licitaciones")
async def crear_historico_licitacion(req: HistoricoLicitacionRequest, db: Session = Depends(get_db)):
    if not (req.cliente or "").strip():
        raise HTTPException(status_code=400, detail="Cliente es obligatorio")
    fecha_cierre = datetime.utcnow()
    if (req.fecha_cierre or "").strip():
        try:
            fecha_cierre = datetime.fromisoformat(req.fecha_cierre)
        except Exception:
            raise HTTPException(status_code=400, detail="fecha_cierre invalida, usa formato ISO")

    h = HistoricoLicitacion(
        codigo_licitacion=(req.codigo_licitacion or "").strip().upper(),
        cliente=(req.cliente or "").strip(),
        rubro=(req.rubro or "").strip(),
        monto_ofertado=req.monto_ofertado or 0.0,
        margen_pct=req.margen_pct or 0.0,
        fue_adjudicada=bool(req.fue_adjudicada),
        fecha_cierre=fecha_cierre,
        observaciones=req.observaciones or "",
    )
    db.add(h)
    db.commit()
    db.refresh(h)
    return {"id": h.id, "message": "Historico registrado"}


@app.post("/api/historico-licitaciones/importar")
async def importar_historico_licitaciones(file: UploadFile = File(...), db: Session = Depends(get_db)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in {".csv", ".xlsx"}:
        raise HTTPException(status_code=400, detail="Formato no soportado. Usa CSV o XLSX")

    rows = []
    if ext == ".csv":
        content = await file.read()
        text = content.decode("utf-8", errors="ignore")
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            rows.append({(_norm_header(k)): v for k, v in (row or {}).items()})
    else:
        content = await file.read()
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        ws = wb.active
        raw_headers = [cell.value for cell in ws[1]]
        headers = [_norm_header(str(h or "")) for h in raw_headers]
        for r in ws.iter_rows(min_row=2, values_only=True):
            rows.append({headers[i]: r[i] for i in range(len(headers))})

    alias = {
        "codigo": "codigo_licitacion",
        "ot": "codigo_licitacion",
        "codigo_ot": "codigo_licitacion",
        "codigo_licitacion": "codigo_licitacion",
        "cliente": "cliente",
        "mandante": "cliente",
        "rubro": "rubro",
        "categoria": "rubro",
        "monto": "monto_ofertado",
        "monto_ofertado": "monto_ofertado",
        "monto_oferta": "monto_ofertado",
        "margen": "margen_pct",
        "margen_pct": "margen_pct",
        "adjudicada": "fue_adjudicada",
        "fue_adjudicada": "fue_adjudicada",
        "resultado": "fue_adjudicada",
        "fecha": "fecha_cierre",
        "fecha_cierre": "fecha_cierre",
        "observaciones": "observaciones",
        "comentarios": "observaciones",
    }

    imported = 0
    skipped = 0
    errores = []
    for idx, row in enumerate(rows, start=2):
        canon = {}
        for k, v in row.items():
            mapped = alias.get(k, k)
            canon[mapped] = v

        cliente = str(canon.get("cliente") or "").strip()
        if not cliente:
            skipped += 1
            errores.append(f"Fila {idx}: cliente vacio")
            continue

        try:
            h = HistoricoLicitacion(
                codigo_licitacion=str(canon.get("codigo_licitacion") or "").strip().upper(),
                cliente=cliente,
                rubro=str(canon.get("rubro") or "").strip(),
                monto_ofertado=_to_float(canon.get("monto_ofertado"), 0.0),
                margen_pct=_to_float(canon.get("margen_pct"), 0.0),
                fue_adjudicada=_to_bool(canon.get("fue_adjudicada")),
                fecha_cierre=_to_date(canon.get("fecha_cierre")),
                observaciones=str(canon.get("observaciones") or "").strip(),
            )
            db.add(h)
            imported += 1
        except Exception as e:
            skipped += 1
            errores.append(f"Fila {idx}: {str(e)}")

    db.commit()
    return {
        "message": "Importacion completada",
        "archivo": file.filename,
        "importados": imported,
        "omitidos": skipped,
        "errores": errores[:30],
        "template_columnas": [
            "codigo_licitacion",
            "cliente",
            "rubro",
            "monto_ofertado",
            "margen_pct",
            "fue_adjudicada",
            "fecha_cierre",
            "observaciones",
        ],
    }


@app.get("/api/historico-licitaciones")
async def listar_historico_licitaciones(ultimos_anios: int = 3, db: Session = Depends(get_db)):
    limite_fecha = datetime.utcnow() - timedelta(days=max(1, ultimos_anios) * 365)
    historico = (
        db.query(HistoricoLicitacion)
        .filter(HistoricoLicitacion.fecha_cierre >= limite_fecha)
        .order_by(HistoricoLicitacion.fecha_cierre.desc())
        .all()
    )
    return [
        {
            "id": h.id,
            "codigo_licitacion": h.codigo_licitacion or "",
            "cliente": h.cliente or "",
            "rubro": h.rubro or "",
            "monto_ofertado": h.monto_ofertado or 0.0,
            "margen_pct": h.margen_pct or 0.0,
            "fue_adjudicada": bool(h.fue_adjudicada),
            "fecha_cierre": h.fecha_cierre.isoformat() if h.fecha_cierre else "",
            "observaciones": h.observaciones or "",
        }
        for h in historico
    ]


@app.post("/api/prediccion/atractividad")
async def evaluar_atractividad(req: AtractividadRequest, db: Session = Depends(get_db)):
    proyecto = db.query(Proyecto).filter(Proyecto.id == req.proyecto_id).first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    pred_actual = calcular_prediccion(proyecto.datos_extraidos or {}, req.factores or {})
    limite_fecha = datetime.utcnow() - timedelta(days=3 * 365)
    historico = (
        db.query(HistoricoLicitacion)
        .filter(HistoricoLicitacion.fecha_cierre >= limite_fecha)
        .order_by(HistoricoLicitacion.fecha_cierre.desc())
        .all()
    )
    historico_dict = [
        {
            "codigo_licitacion": h.codigo_licitacion or "",
            "cliente": h.cliente or "",
            "rubro": h.rubro or "",
            "monto_ofertado": h.monto_ofertado or 0.0,
            "margen_pct": h.margen_pct or 0.0,
            "fue_adjudicada": bool(h.fue_adjudicada),
            "fecha_cierre": h.fecha_cierre.isoformat() if h.fecha_cierre else "",
        }
        for h in historico
    ]

    atractividad = calcular_atractividad_licitacion(
        prediccion_actual=pred_actual,
        historico_3y=historico_dict,
        cliente_objetivo=proyecto.cliente or "",
    )

    return {
        "proyecto_id": proyecto.id,
        "codigo_licitacion": proyecto.codigo_licitacion or "",
        "cliente": proyecto.cliente or "",
        "atractividad": atractividad,
    }


@app.post("/api/prediccion/atractividad/ml/train")
async def entrenar_modelo_atractividad_ml(req: TrainMLAtractividadRequest, db: Session = Depends(get_db)):
    limite_fecha = datetime.utcnow() - timedelta(days=max(1, req.ultimos_anios) * 365)
    historico = (
        db.query(HistoricoLicitacion)
        .filter(HistoricoLicitacion.fecha_cierre >= limite_fecha)
        .order_by(HistoricoLicitacion.fecha_cierre.asc())
        .all()
    )
    historico_dict = [
        {
            "cliente": h.cliente or "",
            "rubro": h.rubro or "",
            "monto_ofertado": h.monto_ofertado or 0.0,
            "margen_pct": h.margen_pct or 0.0,
            "fue_adjudicada": bool(h.fue_adjudicada),
        }
        for h in historico
    ]
    trained = train_logistic_model(historico_dict, epochs=req.epochs, lr=req.lr)
    if not trained.get("ok"):
        raise HTTPException(status_code=400, detail=trained.get("error", "No se pudo entrenar modelo ML"))

    payload = {
        "version": "atractividad-ml-v2",
        "trained_at": datetime.utcnow().isoformat(),
        "config": {"ultimos_anios": req.ultimos_anios, "epochs": req.epochs, "lr": req.lr},
        "model": trained["model"],
    }
    ML_ATRACTIVIDAD_MODEL_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "message": "Modelo ML entrenado",
        "model_path": str(ML_ATRACTIVIDAD_MODEL_PATH.relative_to(BASE_DIR)),
        "metrics": {
            "train_size": trained["model"]["train_size"],
            "val_size": trained["model"]["val_size"],
            "accuracy_train": trained["model"]["accuracy_train"],
            "accuracy_val": trained["model"]["accuracy_val"],
        },
    }


@app.get("/api/prediccion/atractividad/ml/status")
async def estado_modelo_atractividad_ml():
    if not ML_ATRACTIVIDAD_MODEL_PATH.exists():
        return {"ready": False, "message": "Modelo ML no entrenado"}
    try:
        payload = json.loads(ML_ATRACTIVIDAD_MODEL_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"ready": False, "message": "Modelo ML corrupto"}
    m = payload.get("model", {})
    return {
        "ready": True,
        "version": payload.get("version", ""),
        "trained_at": payload.get("trained_at", ""),
        "train_size": m.get("train_size", 0),
        "val_size": m.get("val_size", 0),
        "accuracy_train": m.get("accuracy_train", 0),
        "accuracy_val": m.get("accuracy_val", 0),
    }


@app.post("/api/prediccion/atractividad/ml/evaluar")
async def evaluar_atractividad_ml_v2(req: AtractividadMLV2Request, db: Session = Depends(get_db)):
    if not ML_ATRACTIVIDAD_MODEL_PATH.exists():
        raise HTTPException(status_code=400, detail="Modelo ML no entrenado. Ejecuta /api/prediccion/atractividad/ml/train")

    proyecto = db.query(Proyecto).filter(Proyecto.id == req.proyecto_id).first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    payload = json.loads(ML_ATRACTIVIDAD_MODEL_PATH.read_text(encoding="utf-8"))
    model = payload.get("model", {})
    cliente_eval = (req.cliente or "").strip() or (proyecto.cliente or "")
    rubro_eval = (req.rubro or "").strip()
    ml_result = predict_atractividad_ml(
        model=model,
        cliente=cliente_eval,
        rubro=rubro_eval,
        monto_oferta=req.monto_oferta or 0.0,
        margen_pct=req.margen_pct or 0.0,
    )
    return {
        "proyecto_id": proyecto.id,
        "codigo_licitacion": proyecto.codigo_licitacion or "",
        "cliente": cliente_eval,
        "rubro": rubro_eval,
        "resultado_ml": ml_result,
        "modelo": {
            "version": payload.get("version", ""),
            "trained_at": payload.get("trained_at", ""),
            "accuracy_val": model.get("accuracy_val", 0),
        },
    }


@app.post("/api/prediccion/bid-leveling")
async def bid_leveling(req: BidLevelingRequest, db: Session = Depends(get_db)):
    proyecto = db.query(Proyecto).filter(Proyecto.id == req.proyecto_id).first()
    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    if len(req.oferta_ids or []) < 2:
        raise HTTPException(status_code=400, detail="Debes seleccionar al menos 2 ofertas")

    ofertas = (
        db.query(OfertaLicitacion)
        .filter(
            OfertaLicitacion.proyecto_id == req.proyecto_id,
            OfertaLicitacion.id.in_(req.oferta_ids),
        )
        .all()
    )
    if len(ofertas) < 2:
        raise HTTPException(status_code=400, detail="No se encontraron suficientes ofertas para comparar")

    min_monto = min((o.monto_oferta or 0.0) for o in ofertas) or 1.0
    plazos_validos = [o.plazo_dias for o in ofertas if (o.plazo_dias or 0) > 0]
    min_plazo = min(plazos_validos) if plazos_validos else 1

    comparativo = []
    for oferta in ofertas:
        pred = calcular_prediccion(proyecto.datos_extraidos or {}, oferta.factores or {})
        monto = oferta.monto_oferta or 0.0
        plazo = oferta.plazo_dias or 0
        precio_relativo = (monto / min_monto * 100.0) if min_monto > 0 else 100.0
        plazo_relativo = (plazo / min_plazo * 100.0) if plazo > 0 and min_plazo > 0 else 100.0

        comparativo.append({
            "oferta_id": oferta.id,
            "nombre": oferta.nombre,
            "monto_oferta": monto,
            "plazo_dias": plazo,
            "score": pred.get("score", 0.0),
            "score_base": pred.get("score_base", pred.get("score", 0.0)),
            "probabilidad": pred.get("probabilidad_adjudicacion", 0.0),
            "indice_riesgo": pred.get("indice_riesgo", 0.0),
            "precio_relativo_indice": round(precio_relativo, 2),
            "plazo_relativo_indice": round(plazo_relativo, 2),
            "top_riesgos": [r for r in (pred.get("matriz_riesgos", []) or []) if r.get("nivel") == "alto"],
            "prediccion": pred,
        })

    ranking = sorted(
        comparativo,
        key=lambda x: (
            x.get("score", 0.0),
            -(100.0 - min(200.0, x.get("precio_relativo_indice", 100.0))),
            -(100.0 - min(200.0, x.get("plazo_relativo_indice", 100.0))),
        ),
        reverse=True,
    )

    mejor = ranking[0]
    for item in ranking:
        item["brecha_score_vs_mejor"] = round(item["score"] - mejor["score"], 2)
        item["brecha_precio_vs_mejor_pct"] = round(item["precio_relativo_indice"] - mejor["precio_relativo_indice"], 2)
        item["brecha_plazo_vs_mejor_pct"] = round(item["plazo_relativo_indice"] - mejor["plazo_relativo_indice"], 2)
        item["brecha_riesgo_vs_mejor"] = round(item["indice_riesgo"] - mejor["indice_riesgo"], 2)

    resumen = {
        "oferta_recomendada_id": mejor["oferta_id"],
        "oferta_recomendada_nombre": mejor["nombre"],
        "justificacion": (
            f"Mayor score ajustado por riesgo ({mejor['score']:.2f}) "
            f"y probabilidad estimada ({mejor['probabilidad']*100:.2f}%)."
        ),
    }

    return {
        "proyecto_id": req.proyecto_id,
        "cantidad_ofertas": len(ranking),
        "ranking": ranking,
        "resumen": resumen,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
