"""
================================================================================
BIM ECOSYSTEM — App Unificada v1.0
================================================================================
Módulos:
  01 · IDsify       — PDF (BEP/EIR) → IDS XML (buildingSMART 1.0.0)
  02 · Auditoría    — IDS XML + IFC  → Reporte CSV de colisiones
  03 · BIM Fixer    — IFC + CSV      → IFC corregido

Stack: Python 3.12 · Streamlit · IfcOpenShell · Gemini API · lxml
Autor: Generado con Claude (Anthropic) — Ecosistema BIM Infraestructures.cat
================================================================================
"""

# ── DEPENDENCIAS ──────────────────────────────────────────────────────────────
# pip install streamlit PyPDF2 pandas ifcopenshell lxml requests openpyxl

import streamlit as st
import PyPDF2
import pandas as pd
import requests
import json
import re
import time
import tempfile
import os
import xml.etree.ElementTree as ET
import ifcopenshell
import ifcopenshell.guid
import ifcopenshell.util.element
from lxml import etree
from datetime import date

# ── CARGA API KEY (Streamlit Cloud Secrets o sidebar manual) ─────────────────
def get_api_key() -> str:
    """Lee la API key de st.secrets (producción) o del sidebar (desarrollo)."""
    try:
        return st.secrets.get("GEMINI_API_KEY", st.session_state.get("gemini_api_key", ""))
    except Exception:
        return st.session_state.get("gemini_api_key", "")



# ── CONFIGURACIÓN DE PÁGINA ───────────────────────────────────────────────────
st.set_page_config(
    page_title="BIM Ecosystem",
    layout="wide",
    page_icon="⬡",
    initial_sidebar_state="expanded"
)

# ── ESTILOS GLOBALES ──────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&family=Syne:wght@400;600;700;800&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
    background-color: #0a0e1a;
    color: #c9d1e0;
}
.stApp { background-color: #0a0e1a; }
.main .block-container { padding: 2rem 2.5rem 3rem; max-width: 1200px; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background-color: #0d1220;
    border-right: 1px solid #1e2535;
}
section[data-testid="stSidebar"] .block-container { padding: 1.5rem 1rem; }

/* ── Tipografía ── */
h1, h2, h3 { font-family: 'Syne', sans-serif; color: #e8edf5; }
.mono { font-family: 'JetBrains Mono', monospace; }

/* ── Cards ── */
.bim-card {
    background: #111827;
    border: 1px solid #1e2d45;
    border-radius: 10px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
}
.bim-card-accent-blue  { border-left: 3px solid #3b82f6; }
.bim-card-accent-amber { border-left: 3px solid #f59e0b; }
.bim-card-accent-green { border-left: 3px solid #10b981; }
.bim-card-accent-red   { border-left: 3px solid #ef4444; }

/* ── Métricas ── */
.metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px,1fr)); gap: 10px; margin-bottom: 1rem; }
.metric-box {
    background: #111827;
    border: 1px solid #1e2d45;
    border-radius: 8px;
    padding: 14px 12px;
    text-align: center;
}
.metric-val { font-family: 'JetBrains Mono', monospace; font-size: 1.8rem; font-weight: 700; line-height: 1; }
.metric-lbl { font-size: 0.68rem; color: #5a6a85; letter-spacing: 0.1em; text-transform: uppercase; margin-top: 4px; }
.mv-blue  { color: #3b82f6; }
.mv-amber { color: #f59e0b; }
.mv-green { color: #10b981; }
.mv-red   { color: #ef4444; }

/* ── Badges ── */
.badge {
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem; letter-spacing: 0.08em;
    padding: 2px 8px; border-radius: 3px;
    text-transform: uppercase;
}
.badge-attr { background: #0c2340; color: #60a5fa; border: 1px solid #1e3a5f; }
.badge-pset { background: #2a1a00; color: #fbbf24; border: 1px solid #5a3a00; }
.badge-ok   { background: #052e16; color: #4ade80; border: 1px solid #15503a; }
.badge-fail { background: #2d0d0d; color: #f87171; border: 1px solid #5a1a1a; }

/* ── XML Preview ── */
.xml-block {
    background: #080d18;
    border: 1px solid #1e2d45;
    border-radius: 8px;
    padding: 12px 14px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    line-height: 1.8;
    overflow-x: auto;
    max-height: 260px;
    overflow-y: auto;
    color: #7a8aa0;
}
.xml-tag  { color: #60a5fa; }
.xml-attr { color: #fbbf24; }
.xml-val  { color: #34d399; }
.xml-cmt  { color: #374151; }

/* ── Log ── */
.log-block {
    background: #060b14;
    border: 1px solid #1e2d45;
    border-radius: 8px;
    padding: 12px 14px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    line-height: 1.9;
    max-height: 200px;
    overflow-y: auto;
}
.log-ok   { color: #10b981; }
.log-err  { color: #ef4444; }
.log-info { color: #3b82f6; }
.log-warn { color: #f59e0b; }

/* ── Botones ── */
.stButton > button {
    width: 100%;
    font-family: 'Syne', sans-serif;
    font-weight: 600;
    font-size: 0.9rem;
    letter-spacing: 0.04em;
    border-radius: 8px;
    border: none;
    padding: 0.65rem 1rem;
    transition: opacity 0.2s, transform 0.15s;
    cursor: pointer;
}
.stButton > button:hover { opacity: 0.87; transform: translateY(-1px); }
.stButton > button:disabled { opacity: 0.3; transform: none; cursor: not-allowed; }

/* ── Upload ── */
.stFileUploader {
    background: #0d1526 !important;
    border: 1px dashed #1e3055 !important;
    border-radius: 10px !important;
}

/* ── Dataframe ── */
.stDataFrame { border-radius: 8px; overflow: hidden; }

/* ── Divider ── */
hr { border: none; border-top: 1px solid #1a2235; margin: 1.5rem 0; }

/* ── Label ── */
.section-tag {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.65rem; letter-spacing: 0.14em;
    text-transform: uppercase; color: #4a5568;
    margin-bottom: 6px;
}
.brand-title {
    font-family: 'Syne', sans-serif;
    font-size: 2.4rem; font-weight: 800;
    background: linear-gradient(120deg, #3b82f6, #10b981);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    letter-spacing: -0.02em; line-height: 1;
}
.brand-sub {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem; color: #3a4a60; margin-top: 2px;
}

/* ── Pipeline indicator ── */
.pipeline-step {
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem; padding: 4px 10px;
    border-radius: 4px; border: 1px solid #1e2d45;
    color: #4a5568; margin-right: 4px;
}
.pipeline-step.active-blue  { border-color: #3b82f6; color: #3b82f6; background: #0c1e36; }
.pipeline-step.active-amber { border-color: #f59e0b; color: #f59e0b; background: #1f1200; }
.pipeline-step.active-green { border-color: #10b981; color: #10b981; background: #041a10; }
</style>
""", unsafe_allow_html=True)

# ── CONSTANTES Y CONFIG ───────────────────────────────────────────────────────
IDS_NS  = "http://standards.buildingsmart.org/IDS"
IDS_NSM = {"ids": IDS_NS}

# ── SESSION STATE ─────────────────────────────────────────────────────────────
for k, v in {
    "modulo": "IDsify",
    "ids_requisitos_brutos": None,
    "ids_xml_bytes": None,
    "ids_df": None,
    "audit_df": None,
    "gemini_api_key": "",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown('<div class="brand-title">⬡ BIM</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-sub">// Ecosystem v1.0 — Infraestructures.cat</div>', unsafe_allow_html=True)
    st.markdown("---")

    st.markdown('<div class="section-tag">Navegación</div>', unsafe_allow_html=True)
    modulos = {
        "IDsify":     "01 · IDsify — PDF → IDS",
        "Auditoría":  "02 · Auditoría — IDS + IFC",
        "BIM Fixer":  "03 · BIM Fixer — Corrección",
    }
    for key, label in modulos.items():
        if st.button(label, key=f"nav_{key}"):
            st.session_state.modulo = key

    st.markdown("---")
    st.markdown('<div class="section-tag">Configuración API</div>', unsafe_allow_html=True)

    # Si hay secret configurado, no pedir la clave
    _key_from_secret = ""
    try:
        _key_from_secret = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        pass

    if _key_from_secret:
        st.success("✓ API Key configurada")
    else:
        api_key = st.text_input(
            "Gemini API Key",
            value=st.session_state.gemini_api_key,
            type="password",
            placeholder="AIza..."
        )
        if api_key:
            st.session_state.gemini_api_key = api_key


    st.markdown("---")
    st.markdown("""
    <div style="font-family:'JetBrains Mono',monospace; font-size:0.65rem; color:#2a3a50; line-height:1.8">
    Stack:<br>
    · Python 3.12<br>
    · Streamlit<br>
    · IfcOpenShell<br>
    · Gemini 2.5 Flash<br>
    · lxml / IDS 1.0.0
    </div>
    """, unsafe_allow_html=True)

modulo_activo = st.session_state.modulo

# ══════════════════════════════════════════════════════════════════════════════
#  MÓDULO 1 · IDsify — PDF → IDS XML
# ══════════════════════════════════════════════════════════════════════════════

def gemini_request(prompt: str, api_key: str) -> dict | None:
    """Llama a Gemini 2.5 Flash con reintentos simples."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    for intento in range(3):
        try:
            res = requests.post(url, json=payload, timeout=60)
            if res.status_code == 200:
                return res.json()
            elif res.status_code == 429:
                time.sleep(5 * (intento + 1))
            else:
                return None
        except Exception:
            time.sleep(3)
    return None


def limpiar_json(raw: str) -> list:
    """Extrae y parsea JSON de la respuesta de Gemini."""
    raw = raw.strip()
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)
    # Busca el primer '[' y el último ']'
    start = raw.find("[")
    end   = raw.rfind("]") + 1
    if start == -1 or end == 0:
        raise ValueError("No se encontró JSON válido en la respuesta")
    return json.loads(raw[start:end])


def generar_ids_xml(requisitos: list, titulo: str = "Requisitos BIM") -> bytes:
    """
    Genera un XML IDS 1.0.0 válido según el schema buildingSMART.
    Correcciones aplicadas vs código original:
      - Añade elemento <info> obligatorio con <title> y <version>
      - dataType en MAYÚSCULAS (upperCaseName per XSD)
      - Usa <baseName> en properties (no <name>)
      - Diferencia semántica Attribute vs PropertySet
    """
    ns_ids = IDS_NS
    nsmap  = {None: ns_ids}

    root  = etree.Element(f"{{{ns_ids}}}ids", nsmap=nsmap)

    # ── <info> (obligatorio según XSD) ──
    info  = etree.SubElement(root, f"{{{ns_ids}}}info")
    etree.SubElement(info, f"{{{ns_ids}}}title").text       = titulo
    etree.SubElement(info, f"{{{ns_ids}}}version").text     = "1.0.0"
    etree.SubElement(info, f"{{{ns_ids}}}description").text = (
        "Generado automáticamente por BIM Ecosystem — Infraestructures.cat"
    )
    etree.SubElement(info, f"{{{ns_ids}}}date").text = str(date.today())

    specs = etree.SubElement(root, f"{{{ns_ids}}}specifications")

    for r in requisitos:
        ifc_class  = str(r.get("Clase_IFC",  r.get("Clase", "IfcBuildingElement")))
        propiedad  = str(r.get("Propiedad",  r.get("Property", "Name")))
        estructura = str(r.get("Estructura", r.get("Structure", "Attribute"))).lower()
        tipo_dato  = str(r.get("Tipo_Dato",  r.get("DataType", "IFCLABEL"))).upper()  # ← MAYÚSCULAS (fix XSD)
        restriccion = str(r.get("Restriccion_Valor", r.get("Restriccion", r.get("Restriction", "")))).strip()
        req_id      = str(r.get("ID", r.get("Id", f"REQ-{requisitos.index(r)+1:03d}")))
        pset_name   = str(r.get("PropertySet", f"Pset_{ifc_class.replace('Ifc', '')}Common"))

        # <specification>
        spec = etree.SubElement(
            specs, f"{{{ns_ids}}}specification",
            name=req_id, ifcVersion="IFC4"
        )

        # <applicability> → <entity>
        app = etree.SubElement(spec, f"{{{ns_ids}}}applicability")
        ent = etree.SubElement(app,  f"{{{ns_ids}}}entity")
        etree.SubElement(
            etree.SubElement(ent, f"{{{ns_ids}}}name"),
            f"{{{ns_ids}}}simpleValue"
        ).text = ifc_class

        # <requirements>
        reqs = etree.SubElement(spec, f"{{{ns_ids}}}requirements")

        if estructura == "attribute":
            # ── Atributo directo (Name, Tag, Description…) ──
            node = etree.SubElement(reqs, f"{{{ns_ids}}}attribute")
            etree.SubElement(
                etree.SubElement(node, f"{{{ns_ids}}}name"),
                f"{{{ns_ids}}}simpleValue"
            ).text = propiedad
        else:
            # ── PropertySet (Pset_XxxCommon…) ──
            node = etree.SubElement(
                reqs, f"{{{ns_ids}}}property",
                dataType=tipo_dato          # ← siempre UPPERCASE
            )
            etree.SubElement(
                etree.SubElement(node, f"{{{ns_ids}}}propertySet"),
                f"{{{ns_ids}}}simpleValue"
            ).text = pset_name

            # baseName (no name) — fix vs código original
            etree.SubElement(
                etree.SubElement(node, f"{{{ns_ids}}}baseName"),
                f"{{{ns_ids}}}simpleValue"
            ).text = propiedad

        # <value> si hay restricción
        if restriccion and restriccion not in ("", ".*", "None", "nan"):
            etree.SubElement(
                etree.SubElement(node, f"{{{ns_ids}}}value"),
                f"{{{ns_ids}}}simpleValue"
            ).text = restriccion

    return etree.tostring(
        root,
        pretty_print=True,
        xml_declaration=True,
        encoding="UTF-8"
    )


if modulo_activo == "IDsify":
    # ── Header ──
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown("""
        <div style="margin-bottom:6px">
            <span class="pipeline-step active-blue">01 / IDsify</span>
            <span class="pipeline-step">02 / Auditoría</span>
            <span class="pipeline-step">03 / BIM Fixer</span>
        </div>
        """, unsafe_allow_html=True)
        st.title("IDsify — Generador IDS")
        st.markdown(
            '<div class="brand-sub">Transforma tu BEP/EIR en un archivo IDS 1.0.0 válido (buildingSMART)</div>',
            unsafe_allow_html=True
        )
    st.markdown("---")

    col_izq, col_der = st.columns([1, 1.4], gap="large")

    # ── Columna izquierda: carga y configuración ──
    with col_izq:
        st.markdown('<div class="section-tag">Documento de entrada</div>', unsafe_allow_html=True)
        pdf_file = st.file_uploader("BEP / EIR en PDF", type="pdf")

        if pdf_file:
            st.markdown(f"""
            <div class="bim-card bim-card-accent-blue">
            <span class="mono" style="font-size:0.75rem; color:#60a5fa">📄 {pdf_file.name}</span>
            <span style="color:#3a4a60; font-size:0.7rem; margin-left:10px">{pdf_file.size/1024:.0f} KB</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div class="section-tag" style="margin-top:14px">Título del IDS</div>', unsafe_allow_html=True)
        ids_titulo = st.text_input("", value="Requisitos BIM — Infraestructures.cat", label_visibility="collapsed")

        st.markdown('<div class="section-tag" style="margin-top:12px">Motor AI</div>', unsafe_allow_html=True)
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.markdown("""<div class="bim-card"><span style="font-size:0.75rem;color:#5a6a85">Modelo</span><br>
            <span class="mono" style="font-size:0.8rem">gemini-2.5-flash</span></div>""", unsafe_allow_html=True)
        with col_m2:
            st.markdown("""<div class="bim-card"><span style="font-size:0.75rem;color:#5a6a85">IDS Versión</span><br>
            <span class="mono" style="font-size:0.8rem">1.0.0</span></div>""", unsafe_allow_html=True)

        st.markdown("---")
        btn_extraer = st.button(
            "① Extraer Requisitos del PDF",
            disabled=(pdf_file is None or not get_api_key())
        )

        if pdf_file is None:
            st.caption("⬆ Carga un PDF para continuar")
        if not st.session_state.gemini_api_key:
            st.caption("⬅ Introduce tu Gemini API Key en el sidebar")

    # ── Columna derecha: resultados ──
    with col_der:
        if btn_extraer and pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            texto  = " ".join([p.extract_text() or "" for p in reader.pages])

            # Batching — procesamos en lotes de ~3000 chars para evitar 429
            BATCH = 6000
            fragmentos = [texto[i:i+BATCH] for i in range(0, min(len(texto), 30000), BATCH)]
            todos_requisitos = []

            prog = st.progress(0, text="Analizando PDF con Gemini…")
            log_lines = []

            for idx, frag in enumerate(fragmentos):
                prog.progress((idx + 1) / len(fragmentos), text=f"Batch {idx+1}/{len(fragmentos)}…")

                prompt = f"""
Eres un experto en BIM (Building Information Modeling) e IFC.
Analiza el siguiente fragmento de un BEP/EIR y extrae TODOS los requisitos de información.

REGLAS CRÍTICAS:
1. Devuelve SOLO un array JSON, sin texto adicional, sin bloques de código.
2. Diferencia SIEMPRE entre:
   - Atributos de entidad (Name, Tag, Description, ObjectType) → Estructura: "Attribute"
   - Propiedades en PropertySets (cualquier otra propiedad técnica) → Estructura: "Property"
3. Tipo_Dato SIEMPRE en MAYÚSCULAS: IFCLABEL, IFCBOOLEAN, IFCREAL, IFCINTEGER, IFCTEXT
4. Si hay un valor concreto o patrón, ponlo en Restriccion_Valor.
5. Clase_IFC debe ser una clase IFC válida (IfcWall, IfcSlab, IfcColumn, etc.)

Formato JSON esperado:
[
  {{
    "ID": "REQ-001",
    "Clase_IFC": "IfcWall",
    "Propiedad": "Name",
    "Estructura": "Attribute",
    "Tipo_Dato": "IFCLABEL",
    "Restriccion_Valor": "^MUR-.*",
    "PropertySet": ""
  }},
  {{
    "ID": "REQ-002",
    "Clase_IFC": "IfcWall",
    "Propiedad": "IsExternal",
    "Estructura": "Property",
    "Tipo_Dato": "IFCBOOLEAN",
    "Restriccion_Valor": "",
    "PropertySet": "Pset_WallCommon"
  }}
]

FRAGMENTO DEL DOCUMENTO:
{frag}
"""
                resp = gemini_request(prompt, get_api_key())
                if resp:
                    try:
                        raw = resp["candidates"][0]["content"]["parts"][0]["text"]
                        datos = limpiar_json(raw)
                        todos_requisitos.extend(datos)
                        log_lines.append(f'<span class="log-ok">✓ Batch {idx+1}: {len(datos)} requisitos extraídos</span>')
                    except Exception as e:
                        log_lines.append(f'<span class="log-warn">⚠ Batch {idx+1}: parse error — {e}</span>')
                else:
                    log_lines.append(f'<span class="log-err">✗ Batch {idx+1}: sin respuesta de API</span>')
                time.sleep(1.5)

            if todos_requisitos:
                # Deduplicar por ID
                seen = set()
                uniq = []
                for r in todos_requisitos:
                    k = (r.get("Clase_IFC",""), r.get("Propiedad",""))
                    if k not in seen:
                        seen.add(k)
                        uniq.append(r)

                st.session_state.ids_requisitos_brutos = uniq
                st.session_state.ids_df = pd.DataFrame(uniq)

                # Generar XML
                xml_bytes = generar_ids_xml(uniq, ids_titulo)
                st.session_state.ids_xml_bytes = xml_bytes

            st.markdown(
                f'<div class="log-block">{"<br>".join(log_lines)}</div>',
                unsafe_allow_html=True
            )
            prog.progress(1.0, text="✅ Completado")

        # ── Mostrar resultados ──
        if st.session_state.ids_df is not None:
            df = st.session_state.ids_df
            c1, c2, c3 = st.columns(3)
            c1.markdown(f'<div class="metric-box"><div class="metric-val mv-blue">{len(df)}</div><div class="metric-lbl">Requisitos</div></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-box"><div class="metric-val mv-amber">{df["Clase_IFC"].nunique() if "Clase_IFC" in df.columns else "—"}</div><div class="metric-lbl">Clases IFC</div></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-box"><div class="metric-val mv-green">IDS</div><div class="metric-lbl">Estándar</div></div>', unsafe_allow_html=True)

            st.markdown("---")
            st.markdown('<div class="section-tag">Requisitos extraídos</div>', unsafe_allow_html=True)
            st.dataframe(df, use_container_width=True, hide_index=True)

            if st.session_state.ids_xml_bytes:
                st.markdown("---")
                st.markdown('<div class="section-tag">Vista previa XML (IDS 1.0.0)</div>', unsafe_allow_html=True)
                xml_str = st.session_state.ids_xml_bytes.decode("utf-8")
                # Colorear sintaxis básica para el preview
                xml_prev = xml_str[:2000].replace("<", "&lt;").replace(">", "&gt;")
                st.markdown(f'<div class="xml-block"><pre style="margin:0">{xml_prev}…</pre></div>', unsafe_allow_html=True)

                st.download_button(
                    label="⬇ Descargar IDS XML (buildingSMART 1.0.0)",
                    data=st.session_state.ids_xml_bytes,
                    file_name=f"IDS_{ids_titulo.replace(' ','_')}.xml",
                    mime="application/xml",
                    use_container_width=True
                )
        else:
            st.markdown("""
            <div class="bim-card" style="text-align:center; padding:3rem 1rem; color:#2a3a50">
                <div style="font-size:2rem; margin-bottom:8px">⬡</div>
                <div class="mono" style="font-size:0.8rem">Esperando documento PDF…</div>
            </div>
            """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  MÓDULO 2 · AUDITORÍA BIM — IDS + IFC → CSV
# ══════════════════════════════════════════════════════════════════════════════

def es_numero(v: str) -> bool:
    try:
        float(v)
        return True
    except (ValueError, TypeError):
        return False


def parsear_ids(xml_file) -> list:
    """
    Parsea el IDS XML según el schema buildingSMART 1.0.0.
    Soporta facets: attribute y property.
    """
    reglas = []
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
    except Exception as e:
        st.error(f"Error parseando IDS: {e}")
        return reglas

    for spec in root.findall(".//ids:specification", IDS_NSM):
        # Clase IFC de applicability
        ent_node = spec.find(".//ids:applicability/ids:entity/ids:name/ids:simpleValue", IDS_NSM)
        if ent_node is None:
            continue
        ifc_class = ent_node.text.strip()

        for req in spec.findall(".//ids:requirements/*", IDS_NSM):
            tag = req.tag.split("}")[-1]  # attribute | property | material | etc.

            if tag == "attribute":
                name_node = req.find(".//ids:name/ids:simpleValue", IDS_NSM)
                if name_node is None:
                    continue
                prop_name = name_node.text.strip()
                estructura = "attribute"

            elif tag == "property":
                name_node = req.find(".//ids:baseName/ids:simpleValue", IDS_NSM)
                if name_node is None:
                    continue
                prop_name = name_node.text.strip()
                estructura = "property"

            else:
                continue  # material, partOf, classification → futura extensión

            val_node = req.find(".//ids:value/ids:simpleValue", IDS_NSM)
            restriccion = val_node.text.strip() if val_node is not None else ".*"

            reglas.append({
                "Clase_IFC":   ifc_class,
                "Propiedad":   prop_name,
                "Estructura":  estructura,
                "Restriccion": restriccion,
            })

    return reglas


def auditar_modelo(reglas: list, ifc_path: str) -> pd.DataFrame:
    """Motor de validación IDS vs IFC."""
    model = ifcopenshell.open(ifc_path)
    resultados = []

    for r in reglas:
        try:
            elementos = model.by_type(r["Clase_IFC"])
        except Exception:
            continue

        for el in elementos:
            val = "N/A"
            p   = r["Propiedad"]

            # Búsqueda 1: atributo directo
            if hasattr(el, p) and getattr(el, p) is not None:
                val = str(getattr(el, p))

            # Búsqueda 2: PropertySets
            if val == "N/A":
                try:
                    psets = ifcopenshell.util.element.get_psets(el)
                    for _, d in psets.items():
                        if p in d:
                            val = str(d[p])
                            break
                        # Alias semánticos
                        aliases = {
                            "OverallWidth":  "Width",
                            "IsStructural":  "LoadBearing",
                            "FireRating":    "FireResistanceRating",
                        }
                        if p in aliases and aliases[p] in d:
                            val = str(d[aliases[p]])
                            break
                except Exception:
                    pass

            # Validación
            patron  = r["Restriccion"].replace("^", "").replace("$", "").strip()
            val_str = str(val).strip()
            cumple  = False

            if val_str not in ("N/A", "None", ""):
                if es_numero(val_str) and es_numero(patron):
                    cumple = float(val_str) == float(patron)
                else:
                    try:
                        cumple = bool(re.search(r["Restriccion"], val_str, re.IGNORECASE))
                    except re.error:
                        cumple = (val_str.lower() == patron.lower())

            # GUID normalizado (22-char → 36-char)
            guid_22 = el.GlobalId
            try:
                guid_36 = ifcopenshell.guid.expand(guid_22)
            except Exception:
                guid_36 = guid_22

            resultados.append({
                "GUID":      guid_22,
                "GUID_UUID": guid_36,
                "Clase":     r["Clase_IFC"],
                "Parámetro": p,
                "Requisito": patron,
                "Modelo":    val_str,
                "Estado":    "✅ PASA" if cumple else "❌ FALLA",
            })

    return pd.DataFrame(resultados)


if modulo_activo == "Auditoría":
    st.markdown("""
    <div style="margin-bottom:6px">
        <span class="pipeline-step">01 / IDsify</span>
        <span class="pipeline-step active-amber">02 / Auditoría</span>
        <span class="pipeline-step">03 / BIM Fixer</span>
    </div>
    """, unsafe_allow_html=True)
    st.title("Auditoría BIM — Validación IDS")
    st.markdown('<div class="brand-sub">Detecta colisiones informativas entre tu modelo IFC y los requisitos IDS</div>', unsafe_allow_html=True)
    st.markdown("---")

    col_izq, col_der = st.columns([1, 1.4], gap="large")

    with col_izq:
        st.markdown('<div class="section-tag">Archivo IDS (.xml)</div>', unsafe_allow_html=True)
        ids_upload = st.file_uploader("IDS buildingSMART", type=["xml", "ids"], key="aud_ids")

        st.markdown('<div class="section-tag" style="margin-top:14px">Modelo IFC</div>', unsafe_allow_html=True)
        ifc_upload = st.file_uploader("Modelo Federado (.ifc)", type="ifc", key="aud_ifc")

        if ids_upload:
            st.markdown(f'<div class="bim-card bim-card-accent-amber"><span class="mono" style="color:#fbbf24;font-size:0.75rem">📋 {ids_upload.name}</span></div>', unsafe_allow_html=True)
        if ifc_upload:
            st.markdown(f'<div class="bim-card bim-card-accent-blue"><span class="mono" style="color:#60a5fa;font-size:0.75rem">🏗 {ifc_upload.name}</span> <span style="color:#3a4a60;font-size:0.7rem">{ifc_upload.size/1024/1024:.1f} MB</span></div>', unsafe_allow_html=True)

        st.markdown("---")
        btn_auditar = st.button(
            "② Ejecutar Auditoría IDS",
            disabled=(ids_upload is None or ifc_upload is None)
        )

    with col_der:
        if btn_auditar and ids_upload and ifc_upload:
            with st.spinner("Abriendo modelo IFC…"):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp:
                    tmp.write(ifc_upload.getbuffer())
                    ifc_path = tmp.name

            with st.spinner("Parseando IDS…"):
                reglas = parsear_ids(ids_upload)
                st.info(f"📋 {len(reglas)} reglas encontradas en el IDS")

            if reglas:
                prog = st.progress(0, text="Validando elementos…")
                log  = st.empty()

                log_lines = [
                    '<span class="log-info">▶ Iniciando motor de auditoría…</span>',
                    f'<span class="log-info">▶ Reglas IDS cargadas: {len(reglas)}</span>',
                ]
                log.markdown(f'<div class="log-block">{"<br>".join(log_lines)}</div>', unsafe_allow_html=True)

                # Procesar
                df_result = auditar_modelo(reglas, ifc_path)
                st.session_state.audit_df = df_result

                log_lines.append(f'<span class="log-ok">✓ {len(df_result)} validaciones completadas</span>')
                fallos = len(df_result[df_result["Estado"].str.contains("FALLA", na=False)])
                log_lines.append(f'<span class="log-warn">⚠ {fallos} colisiones detectadas</span>')
                log.markdown(f'<div class="log-block">{"<br>".join(log_lines)}</div>', unsafe_allow_html=True)
                prog.progress(1.0, text="✅ Auditoría completada")

                try:
                    os.unlink(ifc_path)
                except Exception:
                    pass

        # ── Resultados ──
        if st.session_state.audit_df is not None:
            df = st.session_state.audit_df
            total  = len(df)
            pasan  = len(df[df["Estado"].str.contains("PASA", na=False)])
            fallan = len(df[df["Estado"].str.contains("FALLA", na=False)])
            pct    = round((pasan / total) * 100, 1) if total > 0 else 0

            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f'<div class="metric-box"><div class="metric-val mv-blue">{total}</div><div class="metric-lbl">Revisados</div></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-box"><div class="metric-val mv-green">{pasan}</div><div class="metric-lbl">Pasan</div></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-box"><div class="metric-val mv-red">{fallan}</div><div class="metric-lbl">Fallan</div></div>', unsafe_allow_html=True)
            c4.markdown(f'<div class="metric-box"><div class="metric-val mv-amber">{pct}%</div><div class="metric-lbl">Cumplimiento</div></div>', unsafe_allow_html=True)

            st.markdown("---")

            # Filtro rápido
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                filtro_estado = st.selectbox("Filtrar por estado", ["Todos", "Solo fallos", "Solo pasan"])
            with col_f2:
                clases = ["Todas"] + sorted(df["Clase"].unique().tolist())
                filtro_clase = st.selectbox("Filtrar por clase IFC", clases)

            df_show = df.copy()
            if filtro_estado == "Solo fallos":
                df_show = df_show[df_show["Estado"].str.contains("FALLA", na=False)]
            elif filtro_estado == "Solo pasan":
                df_show = df_show[df_show["Estado"].str.contains("PASA", na=False)]
            if filtro_clase != "Todas":
                df_show = df_show[df_show["Clase"] == filtro_clase]

            st.dataframe(df_show, use_container_width=True, hide_index=True)

            csv_bytes = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇ Descargar Reporte CSV",
                data=csv_bytes,
                file_name="Reporte_Auditoria_BIM.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.markdown("""
            <div class="bim-card" style="text-align:center; padding:3rem 1rem; color:#2a3a50">
                <div style="font-size:2rem; margin-bottom:8px">⬡</div>
                <div class="mono" style="font-size:0.8rem">Carga el IDS y el IFC para iniciar la auditoría</div>
            </div>
            """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  MÓDULO 3 · BIM FIXER — IFC + CSV → IFC Corregido
# ══════════════════════════════════════════════════════════════════════════════

def normalizar_guid(guid_str: str) -> str:
    """22-char Base64 comprimido → 36-char UUID hexadecimal."""
    guid_str = str(guid_str).strip()
    if len(guid_str) == 22:
        try:
            return ifcopenshell.guid.expand(guid_str)
        except Exception:
            return guid_str
    return guid_str


def comprimir_guid(guid_str: str) -> str:
    """36-char UUID → 22-char Base64 comprimido (formato nativo ifcopenshell)."""
    guid_str = str(guid_str).strip()
    if len(guid_str) == 36:
        try:
            return ifcopenshell.guid.compress(guid_str.replace("-", ""))
        except Exception:
            return guid_str
    return guid_str


def detectar_tipo_ifc(valor_str: str) -> str:
    """Inferencia semántica del tipo IFC correcto para el valor."""
    v = str(valor_str).strip()
    if v.lower() in ["true", "false", "verdadero", "falso", ".t.", ".f."]:
        return "IfcBoolean"
    try:
        float(v)
        return "IfcReal" if "." in v else "IfcInteger"
    except ValueError:
        pass
    return "IfcLabel"


def crear_valor_ifc(model, valor_str: str):
    """Construye la entidad IfcValue correcta."""
    tipo = detectar_tipo_ifc(valor_str)
    try:
        if tipo == "IfcReal":
            return model.create_entity("IfcReal", float(valor_str))
        elif tipo == "IfcInteger":
            return model.create_entity("IfcInteger", int(float(valor_str)))
        elif tipo == "IfcBoolean":
            return model.create_entity("IfcBoolean", valor_str.lower() in ["true", "verdadero", ".t."])
        else:
            return model.create_entity("IfcLabel", str(valor_str))
    except Exception:
        return model.create_entity("IfcLabel", str(valor_str))


def encontrar_elemento(model, guid: str):
    """Búsqueda resiliente por GUID en ambos formatos."""
    for g in [guid, comprimir_guid(guid), normalizar_guid(guid)]:
        try:
            el = model.by_guid(g)
            if el is not None:
                return el
        except Exception:
            continue
    return None


def inyectar_en_pset(model, element, param_name: str, valor_str: str, ifc_class: str):
    """
    Inyección dinámica en PropertySet.
    Crea IfcPropertySet + IfcRelDefinesByProperties si no existen.
    """
    pset_name = f"Pset_{ifc_class.replace('Ifc', '')}Common"
    existing_pset = None

    for rel in getattr(element, "IsDefinedBy", []):
        if rel.is_a("IfcRelDefinesByProperties"):
            prop_def = rel.RelatingPropertyDefinition
            if prop_def.is_a("IfcPropertySet") and prop_def.Name == pset_name:
                existing_pset = prop_def
                break

    valor_ifc = crear_valor_ifc(model, valor_str)

    if existing_pset:
        for prop in existing_pset.HasProperties:
            if prop.Name == param_name:
                prop.NominalValue = valor_ifc
                return True, f"✏ Actualizado en {pset_name}"
        new_prop = model.create_entity("IfcPropertySingleValue", Name=param_name, NominalValue=valor_ifc)
        existing_pset.HasProperties = list(existing_pset.HasProperties) + [new_prop]
        return True, f"➕ Añadido a {pset_name}"
    else:
        owner_history = element.OwnerHistory
        new_prop = model.create_entity("IfcPropertySingleValue", Name=param_name, NominalValue=valor_ifc)
        new_pset = model.create_entity(
            "IfcPropertySet",
            GlobalId=ifcopenshell.guid.new(),
            OwnerHistory=owner_history,
            Name=pset_name,
            HasProperties=[new_prop]
        )
        model.create_entity(
            "IfcRelDefinesByProperties",
            GlobalId=ifcopenshell.guid.new(),
            OwnerHistory=owner_history,
            RelatedObjects=[element],
            RelatingPropertyDefinition=new_pset
        )
        return True, f"🆕 Pset {pset_name} creado + IfcRelDefinesByProperties"


def corregir_elemento(model, guid: str, param_name: str, valor_str: str, ifc_class: str):
    """
    Corrección de un elemento: primero intenta atributo directo,
    luego PropertySet (diferenciación semántica crítica del proyecto).
    """
    element = encontrar_elemento(model, guid)
    if element is None:
        return False, f"GUID no encontrado: {guid[:16]}…"

    # Atributos directos de la entidad IFC
    try:
        atributos = [a[0] for a in element.__class__.attributes()]
    except Exception:
        atributos = []

    if param_name in atributos:
        try:
            setattr(element, param_name, valor_str)
            return True, f"✅ Atributo '{param_name}' corregido"
        except Exception as e:
            return False, f"Error en atributo: {e}"

    # PropertySet
    try:
        return inyectar_en_pset(model, element, param_name, valor_str, ifc_class)
    except Exception as e:
        return False, f"Error en Pset: {e}"


if modulo_activo == "BIM Fixer":
    st.markdown("""
    <div style="margin-bottom:6px">
        <span class="pipeline-step">01 / IDsify</span>
        <span class="pipeline-step">02 / Auditoría</span>
        <span class="pipeline-step active-green">03 / BIM Fixer</span>
    </div>
    """, unsafe_allow_html=True)
    st.title("BIM Fixer — Motor de Corrección")
    st.markdown('<div class="brand-sub">Inyecta correcciones masivas en el modelo IFC basándose en el reporte de auditoría</div>', unsafe_allow_html=True)
    st.markdown("---")

    col_izq, col_der = st.columns([1, 1.4], gap="large")

    with col_izq:
        st.markdown('<div class="section-tag">Modelo IFC Original</div>', unsafe_allow_html=True)
        ifc_fix = st.file_uploader("Archivo IFC a corregir", type="ifc", key="fix_ifc")

        st.markdown('<div class="section-tag" style="margin-top:14px">Reporte de Auditoría (.csv)</div>', unsafe_allow_html=True)

        # Permite cargar CSV o usar el de session_state
        csv_fix = st.file_uploader("CSV generado por Módulo 2", type="csv", key="fix_csv")

        if csv_fix is None and st.session_state.audit_df is not None:
            st.info("✓ Usando reporte de la sesión actual (Módulo 2)")
            df_audit_fix = st.session_state.audit_df
        elif csv_fix is not None:
            try:
                df_audit_fix = pd.read_csv(csv_fix)
            except Exception as e:
                st.error(f"Error leyendo CSV: {e}")
                df_audit_fix = None
        else:
            df_audit_fix = None

        if ifc_fix:
            st.markdown(f'<div class="bim-card bim-card-accent-green"><span class="mono" style="color:#10b981;font-size:0.75rem">🏗 {ifc_fix.name}</span> <span style="color:#3a4a60;font-size:0.7rem">{ifc_fix.size/1024/1024:.1f} MB</span></div>', unsafe_allow_html=True)

        if df_audit_fix is not None:
            col_estado = next((c for c in df_audit_fix.columns if "estado" in c.lower()), None)
            if col_estado:
                fallos_fix = df_audit_fix[df_audit_fix[col_estado].str.contains("FALLA", na=False)]
                st.markdown(f'<div class="bim-card bim-card-accent-red"><span style="color:#ef4444;font-size:0.85rem;font-weight:600">{len(fallos_fix)}</span> <span style="color:#5a6a85;font-size:0.75rem">elementos a corregir</span></div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<div class="section-tag">Estrategia de inyección</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="bim-card" style="padding:12px 14px">
          <div style="margin-bottom:8px"><span class="badge badge-attr">ATTRIBUTE</span> <span style="font-size:0.78rem;color:#5a6a85">setattr() directo en entidad</span></div>
          <div><span class="badge badge-pset">PSET</span> <span style="font-size:0.78rem;color:#5a6a85">IfcPropertySet + IfcRelDefinesByProperties</span></div>
        </div>
        """, unsafe_allow_html=True)

        btn_fix = st.button(
            "③ Ejecutar Corrección Masiva",
            disabled=(ifc_fix is None or df_audit_fix is None)
        )

    with col_der:
        if btn_fix and ifc_fix and df_audit_fix is not None:
            col_estado = next((c for c in df_audit_fix.columns if "estado" in c.lower()), None)
            col_guid   = next((c for c in df_audit_fix.columns if "guid" == c.lower()), df_audit_fix.columns[0])
            col_clase  = next((c for c in df_audit_fix.columns if "clase" in c.lower()), None)
            col_param  = next((c for c in df_audit_fix.columns if "parámetro" in c.lower() or "parametro" in c.lower() or "param" in c.lower()), None)
            col_req    = next((c for c in df_audit_fix.columns if "requisito" in c.lower()), None)

            if not all([col_estado, col_clase, col_param, col_req]):
                st.error("El CSV no tiene las columnas esperadas: Estado, Clase, Parámetro, Requisito")
            else:
                df_fallos = df_audit_fix[df_audit_fix[col_estado].str.contains("FALLA", na=False)].copy()

                if df_fallos.empty:
                    st.success("🎉 El modelo ya cumple todos los requisitos. No hay correcciones necesarias.")
                else:
                    # Tabla editable para revisar valores
                    df_fallos["Valor_Corrección"] = df_fallos[col_req].astype(str)
                    st.markdown('<div class="section-tag">Revisión de valores a inyectar</div>', unsafe_allow_html=True)
                    st.caption("Edita la columna 'Valor_Corrección' si el Requisito es un patrón RegEx.")

                    cols_show = [col_guid, col_clase, col_param, col_req, "Valor_Corrección"]
                    df_editable = st.data_editor(
                        df_fallos[cols_show],
                        column_config={
                            col_guid:  st.column_config.TextColumn("🔑 GUID", width="medium"),
                            col_clase: st.column_config.TextColumn("📦 Clase IFC", width="small"),
                            col_param: st.column_config.TextColumn("⚙ Parámetro", width="small"),
                            col_req:   st.column_config.TextColumn("📋 Requisito", width="medium"),
                            "Valor_Corrección": st.column_config.TextColumn("✏ Valor a inyectar", width="medium"),
                        },
                        use_container_width=True,
                        hide_index=True,
                        num_rows="fixed"
                    )

                    if st.button("🚀 Confirmar y Ejecutar"):
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp:
                            tmp.write(ifc_fix.getbuffer())
                            tmp_path = tmp.name

                        try:
                            model_fix = ifcopenshell.open(tmp_path)
                        except Exception as e:
                            st.error(f"Error abriendo IFC: {e}")
                            os.unlink(tmp_path)
                            st.stop()

                        log_resultados = []
                        exitos = errores = 0
                        t0 = time.time()

                        barra  = st.progress(0, text="Iniciando…")
                        log_ph = st.empty()
                        log_lines_fix = []
                        total_fix = len(df_editable)

                        for i, (_, row) in enumerate(df_editable.iterrows()):
                            guid   = str(row[col_guid]).strip()
                            param  = str(row[col_param]).strip()
                            valor  = str(row["Valor_Corrección"]).strip()
                            clase  = str(row[col_clase]).strip()

                            ok, msg = corregir_elemento(model_fix, guid, param, valor, clase)

                            if ok:
                                exitos += 1
                                log_lines_fix.append(f'<span class="log-ok">[{i+1}/{total_fix}] {clase} · {param} → {valor} | {msg}</span>')
                            else:
                                errores += 1
                                log_lines_fix.append(f'<span class="log-err">[{i+1}/{total_fix}] {guid[:12]}… | {msg}</span>')

                            log_resultados.append({
                                "GUID_22chars": comprimir_guid(guid),
                                "GUID_36chars": normalizar_guid(guid),
                                "Clase IFC":    clase,
                                "Parámetro":    param,
                                "Valor_Inyectado": valor,
                                "Resultado":    msg,
                            })

                            barra.progress((i+1)/total_fix, text=f"Corrigiendo {i+1}/{total_fix}…")
                            log_ph.markdown(
                                f'<div class="log-block">{"<br>".join(log_lines_fix[-14:])}</div>',
                                unsafe_allow_html=True
                            )

                        t_total = round(time.time() - t0, 2)

                        # Guardar IFC corregido
                        out_path = tmp_path.replace(".ifc", "_CORREGIDO.ifc")
                        model_fix.write(out_path)
                        with open(out_path, "rb") as f:
                            ifc_bytes = f.read()

                        try:
                            os.unlink(tmp_path)
                            os.unlink(out_path)
                        except Exception:
                            pass

                        st.markdown("---")
                        # Métricas finales
                        r1, r2, r3 = st.columns(3)
                        r1.markdown(f'<div class="metric-box"><div class="metric-val mv-green">{exitos}</div><div class="metric-lbl">Corregidos</div></div>', unsafe_allow_html=True)
                        r2.markdown(f'<div class="metric-box"><div class="metric-val mv-red">{errores}</div><div class="metric-lbl">Errores</div></div>', unsafe_allow_html=True)
                        r3.markdown(f'<div class="metric-box"><div class="metric-val mv-amber">{t_total}s</div><div class="metric-lbl">Tiempo total</div></div>', unsafe_allow_html=True)

                        st.markdown(f"""
                        <div class="bim-card bim-card-accent-green" style="margin-top:10px">
                        <span class="mono" style="font-size:0.78rem;color:#10b981">
                        ⚡ {total_fix} elementos procesados en {t_total}s
                        — reducción estimada vs manual: {round(total_fix * 0.5 / 60, 1)} horas → {t_total}s
                        </span>
                        </div>
                        """, unsafe_allow_html=True)

                        df_log = pd.DataFrame(log_resultados)
                        with st.expander("📋 Log completo de correcciones"):
                            st.dataframe(df_log, use_container_width=True)

                        d1, d2 = st.columns(2)
                        with d1:
                            st.download_button(
                                "⬇ IFC Corregido",
                                ifc_bytes,
                                "Modelo_BIM_Corregido.ifc",
                                "application/octet-stream",
                                use_container_width=True
                            )
                        with d2:
                            st.download_button(
                                "⬇ Log CSV",
                                df_log.to_csv(index=False).encode("utf-8"),
                                "Log_BIMFixer.csv",
                                "text/csv",
                                use_container_width=True
                            )
        else:
            if df_audit_fix is None:
                st.markdown("""
                <div class="bim-card" style="text-align:center; padding:3rem 1rem; color:#2a3a50">
                    <div style="font-size:2rem; margin-bottom:8px">⬡</div>
                    <div class="mono" style="font-size:0.8rem">Carga el IFC y el CSV de auditoría</div>
                </div>
                """, unsafe_allow_html=True)
