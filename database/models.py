from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./docpresupuesto.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Proyecto(Base):
    __tablename__ = "proyectos"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    codigo_licitacion = Column(String, index=True, default="")
    cliente = Column(String)
    descripcion = Column(Text)
    estado = Column(String, default="activo")
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    archivo_base = Column(String)  # Path al archivo subido
    datos_extraidos = Column(JSON)  # Datos extraídos por IA
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow)

class Documento(Base):
    __tablename__ = "documentos"
    id = Column(Integer, primary_key=True, index=True)
    proyecto_id = Column(Integer)
    tipo = Column(String)  # presupuesto, informe_tecnico, bases, contrato, etc.
    nombre = Column(String)
    contenido = Column(Text)
    datos_json = Column(JSON)
    archivo_generado = Column(String)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)

class ItemPresupuesto(Base):
    __tablename__ = "items_presupuesto"
    id = Column(Integer, primary_key=True, index=True)
    proyecto_id = Column(Integer)
    documento_id = Column(Integer)
    partida = Column(String)
    descripcion = Column(Text)
    unidad = Column(String)
    cantidad = Column(Float)
    precio_unitario = Column(Float)
    precio_total = Column(Float)
    categoria = Column(String)
    orden = Column(Integer)

class OfertaLicitacion(Base):
    __tablename__ = "ofertas_licitacion"
    id = Column(Integer, primary_key=True, index=True)
    proyecto_id = Column(Integer, index=True)
    nombre = Column(String, index=True)
    monto_oferta = Column(Float, default=0.0)
    plazo_dias = Column(Integer, default=0)
    factores = Column(JSON)
    notas = Column(Text)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)

class PrediccionAdjudicacion(Base):
    __tablename__ = "predicciones_adjudicacion"
    id = Column(Integer, primary_key=True, index=True)
    proyecto_id = Column(Integer, index=True)
    oferta_id = Column(Integer, index=True)
    score = Column(Float, default=0.0)
    probabilidad = Column(Float, default=0.0)
    resultado_json = Column(JSON)
    version_modelo = Column(String, default="rules-v1")
    fecha_creacion = Column(DateTime, default=datetime.utcnow)

class RequisitoDocumental(Base):
    __tablename__ = "requisitos_documentales"
    id = Column(Integer, primary_key=True, index=True)
    proyecto_id = Column(Integer, index=True)
    nombre = Column(String, index=True)
    categoria = Column(String, default="administrativo")  # tecnico, administrativo, legal, hse
    estado = Column(String, default="pendiente")  # pendiente, en_revision, cumplido
    observaciones = Column(Text, default="")
    fuente = Column(String, default="manual")  # ia, manual
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow)

class EvidenciaRequisito(Base):
    __tablename__ = "evidencias_requisito"
    id = Column(Integer, primary_key=True, index=True)
    proyecto_id = Column(Integer, index=True)
    requisito_id = Column(Integer, index=True)
    nombre_archivo = Column(String)
    extension = Column(String, default="")
    archivo_path = Column(String)
    carpeta_relativa = Column(String)
    orden = Column(Integer, default=0)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)

class HistoricoLicitacion(Base):
    __tablename__ = "historico_licitaciones"
    id = Column(Integer, primary_key=True, index=True)
    codigo_licitacion = Column(String, index=True, default="")
    cliente = Column(String, index=True, default="")
    rubro = Column(String, default="")
    monto_ofertado = Column(Float, default=0.0)
    margen_pct = Column(Float, default=0.0)
    fue_adjudicada = Column(Boolean, default=False)
    fecha_cierre = Column(DateTime, default=datetime.utcnow, index=True)
    observaciones = Column(Text, default="")
    fecha_creacion = Column(DateTime, default=datetime.utcnow)

class LegalAceptacionProyecto(Base):
    __tablename__ = "legal_aceptaciones_proyecto"
    id = Column(Integer, primary_key=True, index=True)
    proyecto_id = Column(Integer, index=True)
    accepted = Column(Boolean, default=False)
    accepted_at = Column(DateTime, default=datetime.utcnow, index=True)
    terms_version = Column(String, default="v1.0.0")
    accepted_source = Column(String, default="frontend-local")
    accepted_by = Column(String, default="")
    metadata_json = Column(JSON)
    fecha_registro = Column(DateTime, default=datetime.utcnow)

class PlanCierreItem(Base):
    __tablename__ = "plan_cierre_items"
    id = Column(Integer, primary_key=True, index=True)
    proyecto_id = Column(Integer, index=True)
    titulo = Column(String, index=True)
    prioridad = Column(String, default="media")  # alta, media, baja
    owner = Column(String, default="equipo")
    estado = Column(String, default="pendiente")  # pendiente, en_progreso, resuelto
    origen = Column(String, default="manual")  # preflight, manual
    fecha_compromiso = Column(DateTime, index=True)
    metadata_json = Column(JSON)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow)

def create_tables():
    Base.metadata.create_all(bind=engine)
    # Migracion ligera para sqlite local: agregar columnas nuevas sin romper BD existente.
    with engine.begin() as conn:
        cols = conn.exec_driver_sql("PRAGMA table_info(proyectos)").fetchall()
        nombres = {c[1] for c in cols}
        if "codigo_licitacion" not in nombres:
            conn.exec_driver_sql("ALTER TABLE proyectos ADD COLUMN codigo_licitacion VARCHAR DEFAULT ''")
        cols_cierre = conn.exec_driver_sql("PRAGMA table_info(plan_cierre_items)").fetchall()
        nombres_cierre = {c[1] for c in cols_cierre}
        if cols_cierre and "fecha_compromiso" not in nombres_cierre:
            conn.exec_driver_sql("ALTER TABLE plan_cierre_items ADD COLUMN fecha_compromiso DATETIME")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
