import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime, date
import pytz
import os
import requests
import altair as alt
import unicodedata
import random


# --------------------------------------------------
# Normalización de texto
# --------------------------------------------------
def _normalize_text(s: str) -> str:
    """
    Normaliza texto para comparaciones robustas:
    - Convierte a string
    - Quita espacios al inicio y final
    - Pasa a minúsculas
    - Elimina acentos
    - Quita caracteres que no sean letras o números
    """
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    s = str(s).strip().lower()

    # Quitar acentos
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")

    # Quitar espacios y signos de puntuación, dejar solo letras y números
    s = "".join(ch for ch in s if ch.isalnum())
    return s


def norm(s: str) -> str:
    """Alias de _normalize_text para nombres de columnas, etc."""
    return _normalize_text(s)


def norm_producto(s: str) -> str:
    """Normalizador específico para nombres de producto."""
    return _normalize_text(s)


# --------------------------------------------------
# Tema Altair
# --------------------------------------------------
def hp_altair_theme():
    return {
        "config": {
            "background": "rgba(0,0,0,0)",
            "view": {"stroke": "transparent"},
            "axis": {
                "labelColor": "#64748B",  # slate-500
                "titleColor": "#0F172A",  # slate-900
                "gridColor": "#E5E7EB",
            },
            "legend": {
                "labelColor": "#0F172A",
                "titleColor": "#0F172A",
            },
            "line": {
                "strokeWidth": 3,
            },
            "range": {
                "category": [
                    "#0F172A",  # negro para Masaryk
                    "#06B6D4",  # cyan
                    "#A855F7",  # violeta
                    "#22C55E",  # verde
                    "#F97316",  # naranja
                    "#EC4899",  # rosa
                ]
            },
        }
    }


alt.themes.register("hp_theme", hp_altair_theme)
alt.themes.enable("hp_theme")

# --------------------------------------------------
# Configuración básica de la página
# --------------------------------------------------
LOGO_URL = "https://raw.githubusercontent.com/apalma-hps/Dashboard-Ventas-HP/49cbb064b6dcf8eecaa4fb39292d9fe94f357d49/logo_hp.png"

st.set_page_config(
    page_title="Inventario – Movimientos",
    page_icon=LOGO_URL,
    layout="wide"
)

# --------------------------------------------------
# THEME VISUAL (CSS)
# --------------------------------------------------
st.markdown(
    """
<style>
    body {
        background: #E5F3FF !important;
    }

    .stApp {
        background: linear-gradient(135deg, #E0F2FE 0%, #ECFDF5 50%, #FDF2F8 100%) !important;
        color: #0F172A !important;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    header[data-testid="stHeader"] {
        background: transparent !important;
    }
    header[data-testid="stHeader"] > div {
        background: transparent !important;
    }

    main.block-container {
        padding-top: 1rem !important;
    }

    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E5E7EB !important;
    }
    section[data-testid="stSidebar"] * {
        color: #0F172A !important;
    }

    h1, h2, h3, .stMarkdown h1, .stMarkdown h2 {
        color: #0F172A !important;
        font-weight: 700 !important;
    }
    h4, h5 {
        color: #111827 !important;
        font-weight: 600 !important;
    }

    label, span, p, li, .stMarkdown, [data-testid="stMarkdownContainer"] * {
        color: #0F172A !important;
    }

    a {
        color: #06B6D4 !important;
        text-decoration: none !important;
    }
    a:hover {
        color: #0E7490 !important;
        text-decoration: underline !important;
    }

    button[kind="primary"],
    button[kind="secondary"],
    button[data-testid^="baseButton"] {
        background: linear-gradient(135deg, #06B6D4, #22C55E) !important;
        color: #FFFFFF !important;
        border-radius: 999px !important;
        border: none !important;
        box-shadow: 0 8px 20px rgba(8, 145, 178, 0.25) !important;
        font-weight: 600 !important;
    }
    button[kind="primary"]:hover,
    button[kind="secondary"]:hover,
    button[data-testid^="baseButton"]:hover {
        background: linear-gradient(135deg, #0891B2, #16A34A) !important;
    }

    [data-testid="stNumberInput"] button {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
        border: 1px solid #D1D5DB !important;
        border-radius: 0.75rem !important;
        box-shadow: none !important;
    }

    input,
    .stTextInput > div > input,
    .stNumberInput input,
    textarea {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
        border: 1px solid #D1D5DB !important;
        border-radius: 0.75rem !important;
        padding: 0.45rem 0.75rem !important;
    }
    input:focus,
    .stTextInput > div > input:focus,
    .stNumberInput input:focus,
    textarea:focus {
        outline: 2px solid #06B6D4 !important;
        border-color: #06B6D4 !important;
    }

    [data-testid="stDateInput"] input {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
        border: 1px solid #D1D5DB !important;
        border-radius: 0.75rem !important;
    }

    div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
        border-radius: 0.75rem !important;
        border: 1px solid #D1D5DB !important;
    }
    div[data-baseweb="select"] svg {
        color: #64748B !important;
    }

    [data-baseweb="menu"],
    [data-baseweb="popover"] [data-baseweb="menu"] {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
        border-radius: 0.75rem !important;
        border: 1px solid #E5E7EB !important;
        box-shadow: 0 18px 45px rgba(15,23,42,0.18) !important;
    }

    [data-baseweb="menu"] ul[role="listbox"],
    [data-baseweb="menu"] div[role="listbox"] {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
    }

    [data-baseweb="menu"] [role="option"],
    [data-baseweb="menu"] li[role="option"] {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
    }

    [data-baseweb="menu"] [role="option"][aria-selected="true"],
    [data-baseweb="menu"] [role="option"]:hover {
        background-color: #DBEAFE !important;
        color: #0F172A !important;
    }

    .dataframe {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
        border-radius: 1rem !important;
        border: 1px solid #E5E7EB !important;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06) !important;
    }

    [data-testid="stDataFrame"],
    [data-testid="stTable"] {
        background-color: #FFFFFF !important;
    }

    [data-testid="stDataFrame"] table,
    [data-testid="stTable"] table {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
    }

    [data-testid="stDataFrame"] th,
    [data-testid="stTable"] th {
        background-color: #F8FAFC !important;
        color: #0F172A !important;
        font-weight: 600 !important;
    }

    [data-testid="stDataFrame"] td,
    [data-testid="stTable"] td {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
    }

    [data-testid="stDataFrame"] tr:hover td,
    [data-testid="stTable"] tr:hover td {
        background-color: #F1F5F9 !important;
    }

    [data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border-radius: 1.5rem !important;
        padding: 1.2rem 1.5rem !important;
        box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08) !important;
        border: 1px solid rgba(148, 163, 184, 0.25) !important;
    }

    .stSuccess {
        background-color: #ECFDF5 !important;
        color: #16A34A !important;
        border-left: 4px solid #16A34A !important;
    }
    .stError {
        background-color: #FEF2F2 !important;
        color: #DC2626 !important;
        border-left: 4px solid #DC2626 !important;
    }
    .stWarning {
        background-color: #FFFBEB !important;
        color: #92400E !important;
        border-left: 4px solid #F59E0B !important;
    }

</style>
""",
    unsafe_allow_html=True,
)

# --------------------------------------------------
# Encabezado con logo
# --------------------------------------------------
st.markdown(
    f"""
    <div style="
        display:flex;
        align-items:center;
        gap:20px;
        margin-top:10px;
        margin-bottom:25px;
        padding:18px 22px;
        background-color: rgba(255,255,255,0.9);
        border-radius: 24px;
        box-shadow: 0 18px 45px rgba(15,23,42,0.08);
    ">
        <img src="{LOGO_URL}" 
             style="
                width:80px; 
                height:80px; 
                object-fit:contain; 
                border-radius:50%; 
                background:white;
                box-shadow: 0 4px 12px rgba(15,23,42,0.18);
             "/>
        <div>
            <h1 style="
                font-size: 1.9rem; 
                font-weight:700; 
                margin:0; 
                padding:0;
                color:#0F172A;
            ">
                Sistema de Gestión de Inventario y Requerimientos
            </h1>
            <p style="
                margin:4px 0 0 0;
                color:#64748B;
                font-size:0.95rem;
            ">
                Operación diaria · Control de insumos · Trazabilidad por restaurante
            </p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------
# URL plantilla inventario (por si se usa después)
# --------------------------------------------------
PLANTILLA_INVENTARIO_XLSX_URL = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vQ4Q30Ldblb-_bxRPugOXBCGU97CrsHozkf0conSHypwdVruRtH9UNXeT2D9mdu8XfDLknMk1UH2UBs/"
    "pub?output=xlsx"
)

# --------------------------------------------------
# Columnas inventario / requerimientos / recepción
# --------------------------------------------------
USER_COLUMNS = [
    "Tipo",
    "CECO_Origen",
    "CECO_Destino",
    "Proveedor",
    "Pedido_Ref",
    "SKU",
    "Producto",
    "Cantidad",
    "UoM",
    "Precio_Unitario",
    "Subtotal",
    "Lote",
    "Caducidad",
    "Temperatura",
    "Observaciones",
    "Folio",
    "Usuario",
    "Chofer",
    "Unidad",
    "Recibido",
    "CECO_DESTINO",
]

REQUERIMIENTOS_COLUMNS = [
    "FECHA DE PEDIDO",
    "PROVEDOR",
    "INSUMO",
    "UNIDAD DE MEDIDA",
    "COSTO UNIDAD",
    "CANTIDAD",
    "COSTO TOTAL",
    "FECHA DESEADA",
    "OBSERVACIONES",
    "ESTATUS",
    "ID_REQ",
    "Hora",
    "CECO_DESTINO",
    "CATEGORIA",
    "Fecha aproximada de entrega",
    "SKU",
]

# Para enviar a Apps Script de recepción (hoja Recepción o script que actualiza Requerimientos)
RECEPCION_COLUMNS = [
    "Fecha de recepción",
    "PROVEEDOR",
    "FACTURA / TICKET",
    "SKU",
    "PRODUCTO",
    "UNIDAD DE MEDIDA",
    "CANTIDAD PO",
    "CANTIDAD RECIBIDA",
    "TEMP (°C)",
    "CALIDAD (OK / RECHAZO)",
    "OBSERVACIONES",
    "RECIBIÓ",
    "FOLIO",
    "APROBÓ",
    "ID DE REQUERIMIENTO AL QUE CORRESPONDE",
    "Folio Generado de Recepcion",
    "fecha de caducidad",
]

# --------------------------------------------------
# Session state
# --------------------------------------------------
if "ultimo_inventario_df" not in st.session_state:
    st.session_state["ultimo_inventario_df"] = None
if "ultimo_inventario_folio" not in st.session_state:
    st.session_state["ultimo_inventario_folio"] = None
if "ultimo_inventario_fecha" not in st.session_state:
    st.session_state["ultimo_inventario_fecha"] = None
if "ultimo_inventario_hora" not in st.session_state:
    st.session_state["ultimo_inventario_hora"] = None

if "carrito_req" not in st.session_state:
    st.session_state["carrito_req"] = []
if "carrito_recepcion" not in st.session_state:
    st.session_state["carrito_recepcion"] = []

if "req_recepcion_df" not in st.session_state:
    st.session_state["req_recepcion_df"] = None
if "req_recepcion_id" not in st.session_state:
    st.session_state["req_recepcion_id"] = ""

# ✅ FIX #3: Contador para forzar recreación del data_editor
if "editor_version" not in st.session_state:
    st.session_state["editor_version"] = 0


# --------------------------------------------------
# Funciones auxiliares – Inventario (por si las usas)
# --------------------------------------------------
@st.cache_data
def load_movimientos_template_from_gsheet() -> pd.DataFrame:
    sheet_url = st.secrets["MOVIMIENTOS_TEMPLATE_CSV_URL"]

    try:
        df = pd.read_csv(sheet_url, nrows=0)
    except pd.errors.ParserError:
        df_full = pd.read_csv(
            sheet_url,
            engine="python",
            on_bad_lines="skip"
        )
        df = df_full.iloc[0:0].copy()

    df.columns = df.columns.str.strip()
    return df


def df_to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Movimientos") -> BytesIO:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output


def detectar_extension(nombre_archivo: str) -> str:
    return os.path.splitext(nombre_archivo)[1].lower().replace(".", "")


def leer_archivo_movimientos(uploaded_file) -> pd.DataFrame:
    nombre = uploaded_file.name
    ext = detectar_extension(nombre)

    if ext in ["xlsx", "xls"]:
        try:
            df = pd.read_excel(uploaded_file, sheet_name="Movimientos_Inventario")
        except ValueError:
            st.warning(
                "El archivo Excel no tiene una hoja llamada 'Movimientos_Inventario'. "
                "Se leerá la primera hoja disponible; revisa que sea la correcta."
            )
            df = pd.read_excel(uploaded_file)
    elif ext == "csv":
        try:
            df = pd.read_csv(uploaded_file)
        except UnicodeDecodeError:
            df = pd.read_csv(uploaded_file, encoding="latin1")
    else:
        st.error(
            f"Tipo de archivo no soportado: .{ext}. Usa archivos Excel (.xlsx, .xls) o CSV."
        )
        st.stop()

    df.columns = df.columns.astype(str).str.strip()
    return df


def validar_y_ordenar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.astype(str).str.strip()

    missing = [c for c in USER_COLUMNS if c not in df.columns]
    if missing:
        st.error(
            "El archivo cargado no contiene todas las columnas requeridas.\n"
            f"Faltan las columnas: {missing}\n\n"
            "Asegúrate de haber usado la plantilla descargada y de no haber cambiado los nombres."
        )
        st.stop()

    df = df[USER_COLUMNS].copy()
    return df


def generar_folio_inventario() -> tuple[str, str, str]:
    tz = pytz.timezone("America/Mexico_City")
    ahora = datetime.now(tz)
    folio = ahora.strftime("INV-%Y%m%d-%H%M%S")
    fecha = ahora.date().isoformat()
    hora = ahora.strftime("%H:%M:%S")
    return folio, fecha, hora


def agregar_campos_sistema(df: pd.DataFrame, folio: str, fecha: str, hora: str) -> pd.DataFrame:
    df = df.copy()
    df["ID"] = folio
    df["Fecha_Carga"] = fecha
    df["Hora_Carga"] = hora

    ordered_cols = (
            ["ID"] +
            [c for c in USER_COLUMNS if c in df.columns] +
            [c for c in ["Fecha_Carga", "Hora_Carga"] if c in df.columns]
    )
    df = df[ordered_cols]
    return df


def enviar_a_consolidado(df: pd.DataFrame):
    url = st.secrets.get("APPS_SCRIPT_CONSOLIDADO_URL", "")

    if not url:
        st.warning(
            "No se configuró APPS_SCRIPT_CONSOLIDADO_URL en secrets. No se enviará nada al consolidado."
        )
        return

    df_json = df.copy()

    def to_jsonable(x):
        if isinstance(x, (pd.Timestamp, datetime, date)):
            return x.isoformat()
        return x

    # ✅ FIX #4: Usar .map() en lugar de .applymap() (deprecado en pandas 2.1+)
    df_json = df_json.map(to_jsonable)
    df_json = df_json.astype(object).where(pd.notnull(df_json), None)

    rows = df_json.values.tolist()
    payload = {"rows": rows}

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            try:
                data = resp.json()
            except Exception:
                data = {}
            if data.get("status") == "ok":
                st.success(
                    f"Movimientos enviados al consolidado en Google Sheets. "
                    f"Filas insertadas: {data.get('inserted', 'desconocido')}."
                )
            else:
                st.warning(
                    "Se recibió respuesta de Apps Script pero con estado distinto de 'ok'. "
                    f"Respuesta: {data}"
                )
        else:
            st.error(
                f"No se pudo enviar al consolidado. Código HTTP: {resp.status_code}"
            )
    except Exception as e:
        st.error("Error al enviar al consolidado.")
        st.exception(e)


# --------------------------------------------------
# Funciones auxiliares – Catálogo / Requerimientos / Recepción
# --------------------------------------------------
@st.cache_data
def load_catalogo_productos() -> pd.DataFrame:
    """
    Carga el catálogo desde CATALOGO_CSV_URL,
    normaliza columnas y genera PRODUCTO_KEY.
    """
    url = st.secrets.get("CATALOGO_CSV_URL", "")
    if not url:
        raise ValueError(
            "No se encontró CATALOGO_CSV_URL en secrets. "
            "Debes apuntar al CSV de la hoja 'Catálogo'."
        )

    try:
        df = pd.read_csv(url)
    except pd.errors.ParserError:
        df = pd.read_csv(url, engine="python", on_bad_lines="skip")

    df.columns = df.columns.astype(str).str.strip()

    rename_map = {}
    for col in df.columns:
        n = norm(col)
        if n == "nombre":
            rename_map[col] = "Producto"
        elif n in ("categoriadeproducto", "categoríadeproducto"):
            rename_map[col] = "Categoria"
        elif n in ("referenciainterna", "sku"):
            rename_map[col] = "Referencia Interna"
        elif n in ("udmdecompra", "unidaddecompra", "udmcompra"):
            rename_map[col] = "UdM de Compra"
        elif n in ("proveedor", "provedor"):
            rename_map[col] = "Proveedor"

    df = df.rename(columns=rename_map)

    required = ["Producto", "Categoria", "Referencia Interna"]
    for c in required:
        if c not in df.columns:
            raise ValueError(
                "La hoja 'Catálogo' debe contener al menos "
                "'Nombre', 'Categoría de producto' y 'Referencia interna'. "
                f"Columnas leídas: {list(df.columns)}"
            )

    df = df[df["Producto"].notna()].copy()
    df["Producto"] = df["Producto"].astype(str).str.strip()
    df["Categoria"] = df["Categoria"].astype(str).str.strip()
    df["Referencia Interna"] = df["Referencia Interna"].astype(str).str.strip()

    df["UdM de Compra"] = (
        df.get("UdM de Compra", "pz")
        .astype(str)
        .fillna("pz")
        .str.strip()
    )
    df["Proveedor"] = (
        df.get("Proveedor", "")
        .astype(str)
        .fillna("")
        .str.strip()
    )

    df = df[
        (df["Producto"] != "") &
        (df["Producto"].str.lower() != "nan")
        ].reset_index(drop=True)

    df["PRODUCTO_KEY"] = df["Producto"].apply(norm_producto)

    return df


@st.cache_data
def load_requerimientos_from_gsheet() -> pd.DataFrame:
    url = st.secrets.get("REQUERIMIENTOS_CSV_URL", "")
    if not url:
        raise ValueError("No se encontró REQUERIMIENTOS_CSV_URL en secrets.")

    try:
        df = pd.read_csv(url)
    except pd.errors.ParserError:
        df = pd.read_csv(url, engine="python", on_bad_lines="skip")

    df.columns = df.columns.astype(str).str.strip()
    return df


@st.cache_data
def load_recepcion_from_gsheet() -> pd.DataFrame:
    url = st.secrets.get("RECEPCION_CSV_URL", "")
    if not url:
        raise ValueError("No se encontró RECEPCION_CSV_URL en secrets.")

    try:
        df = pd.read_csv(url)
    except pd.errors.ParserError:
        df = pd.read_csv(url, engine="python", on_bad_lines="skip")

    df.columns = df.columns.astype(str).str.strip()
    return df


# --------------------------------------------------
# Funciones para recepciones parciales
# --------------------------------------------------
def calcular_pendientes_por_producto(id_req: str, df_req_folio: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula la cantidad pendiente por producto usando los datos de la misma hoja de requerimientos.
    Las columnas CANTIDAD RECIBIDA y CANTIDAD PENDIENTE ya vienen en df_req_folio.
    """

    # DEBUG
    with st.expander("🔍 DEBUG: Columnas disponibles en requerimiento", expanded=False):
        st.write("**Columnas en df_req_folio:**")
        st.code(list(df_req_folio.columns))
        st.write("**Primeras filas:**")
        st.dataframe(df_req_folio.head(5))

    # Buscar columnas de cantidad recibida y pendiente (pueden tener variaciones en nombre)
    col_cant_recibida = None
    col_cant_pendiente = None

    for col in df_req_folio.columns:
        col_lower = col.lower().strip()
        if "cantidad recibida" in col_lower and col_cant_recibida is None:
            col_cant_recibida = col
        if "cantidad pendiente" in col_lower and col_cant_pendiente is None:
            col_cant_pendiente = col

    # Preparar base del requerimiento agrupando por producto
    group_cols = ["INSUMO"]
    if "SKU" in df_req_folio.columns:
        group_cols = ["INSUMO", "SKU"]

    # Convertir columnas numéricas
    df_req_folio["CANTIDAD"] = pd.to_numeric(df_req_folio["CANTIDAD"], errors="coerce").fillna(0.0)

    if col_cant_recibida:
        df_req_folio[col_cant_recibida] = pd.to_numeric(df_req_folio[col_cant_recibida], errors="coerce").fillna(0.0)

    if col_cant_pendiente:
        df_req_folio[col_cant_pendiente] = pd.to_numeric(df_req_folio[col_cant_pendiente], errors="coerce").fillna(0.0)

    # Agrupar por producto
    agg_dict = {"CANTIDAD": "sum"}
    if col_cant_recibida:
        agg_dict[col_cant_recibida] = "sum"
    if col_cant_pendiente:
        agg_dict[col_cant_pendiente] = "sum"

    base_df = df_req_folio.groupby(group_cols, as_index=False).agg(agg_dict)
    base_df = base_df.rename(columns={"CANTIDAD": "CANTIDAD PO"})

    # Renombrar columnas de recibido y pendiente
    if col_cant_recibida:
        base_df = base_df.rename(columns={col_cant_recibida: "CANTIDAD RECIBIDA TOTAL"})
    else:
        base_df["CANTIDAD RECIBIDA TOTAL"] = 0.0

    # Siempre recalcular pendiente
    base_df["CANTIDAD PENDIENTE"] = (
            base_df["CANTIDAD PO"] - base_df["CANTIDAD RECIBIDA TOTAL"]
    )

    # Seguridad
    base_df["CANTIDAD PENDIENTE"] = (
        base_df["CANTIDAD PENDIENTE"]
        .fillna(0)
        .clip(lower=0)
    )

    # Asegurar que pendiente no sea negativo
    base_df["CANTIDAD PENDIENTE"] = base_df["CANTIDAD PENDIENTE"].clip(lower=0)

    # Asegurar SKU existe
    if "SKU" not in base_df.columns:
        base_df["SKU"] = ""

    # Agregar proveedor
    if "PROVEDOR" in df_req_folio.columns:
        prov_map = df_req_folio[["INSUMO", "PROVEDOR"]].drop_duplicates(subset=["INSUMO"])
        prov_map["INSUMO"] = prov_map["INSUMO"].astype(str).str.strip()
        base_df["INSUMO"] = base_df["INSUMO"].astype(str).str.strip()
        base_df = base_df.merge(prov_map, on="INSUMO", how="left")
        base_df.rename(columns={"PROVEDOR": "PROVEEDOR"}, inplace=True)
    else:
        base_df["PROVEEDOR"] = ""

    # DEBUG: mostrar resultado
    with st.expander("🔍 DEBUG: Resultado de pendientes calculados", expanded=False):
        st.write(f"**Columna de recibido encontrada:** `{col_cant_recibida}`")
        st.write(f"**Columna de pendiente encontrada:** `{col_cant_pendiente}`")
        st.dataframe(base_df)

    return base_df


def obtener_historial_recepciones(id_req: str) -> pd.DataFrame:
    """
    Obtiene el historial de recepciones para un requerimiento.
    Como todo está en la misma hoja, filtra las filas que tienen folio de recepción.
    """
    try:
        load_requerimientos_from_gsheet.clear()
        req_df = load_requerimientos_from_gsheet()
        req_df.columns = req_df.columns.astype(str).str.strip()
    except Exception:
        return pd.DataFrame()

    if req_df.empty or "ID_REQ" not in req_df.columns:
        return pd.DataFrame()

    # Filtrar por ID_REQ
    req_folio = req_df[
        req_df["ID_REQ"].astype(str).str.strip() == id_req.strip()
        ].copy()

    # Buscar columna de folio de recepción
    col_folio_recep = None
    for col in req_folio.columns:
        if "folio" in col.lower() and "recep" in col.lower():
            col_folio_recep = col
            break

    # Solo mostrar filas que tienen folio de recepción (ya fueron recibidas)
    if col_folio_recep and col_folio_recep in req_folio.columns:
        req_folio = req_folio[req_folio[col_folio_recep].notna() & (req_folio[col_folio_recep] != "")]

    return req_folio


def generar_folio_requerimiento() -> tuple[str, str, str]:
    tz = pytz.timezone("America/Mexico_City")
    ahora = datetime.now(tz)
    folio = ahora.strftime("REQ-%Y%m%d-%H%M%S")
    fecha = ahora.date().isoformat()
    hora = ahora.strftime("%H:%M:%S")
    return folio, fecha, hora


def generar_folio_recepcion() -> tuple[str, str, str]:
    tz = pytz.timezone("America/Mexico_City")
    ahora = datetime.now(tz)
    folio = ahora.strftime("REC-%Y%m%d-%H%M%S")
    fecha = ahora.date().isoformat()
    hora = ahora.strftime("%H:%M:%S")
    return folio, fecha, hora


def enviar_requerimientos_a_gsheet(lista_req_data):
    url = st.secrets.get("APPS_SCRIPT_REQUERIMIENTOS_URL", "")

    if not url:
        st.warning(
            "No se configuró APPS_SCRIPT_REQUERIMIENTOS_URL en secrets. No se enviarán los requerimientos."
        )
        return

    rows = []
    for req_data in lista_req_data:
        row = [req_data.get(col, "") for col in REQUERIMIENTOS_COLUMNS]
        rows.append(row)

    payload = {"rows": rows}

    try:
        resp = requests.post(url, json=payload, timeout=10)

        # DEBUG: mostrar siempre la respuesta cruda
        st.markdown("#### Respuesta cruda de Apps Script (requerimientos – debug)")
        st.code(resp.text, language="json")

        if resp.status_code != 200:
            st.error(
                f"No se pudo enviar el requerimiento. Código HTTP: {resp.status_code}"
            )
            return

        try:
            data = resp.json()
        except Exception as e:
            st.warning(
                "La respuesta de Apps Script no es un JSON válido. "
                "Revisa el contenido mostrado arriba (debug)."
            )
            st.exception(e)
            return

        status = data.get("status")
        if status == "ok":
            st.success(
                f"Requerimiento enviado y registrado. "
                f"Filas insertadas: {data.get('inserted', 'desconocido')}."
            )
        else:
            st.warning(
                "Se recibió respuesta de Apps Script pero con estado distinto de 'ok'. "
                f"Respuesta completa: {data}"
            )

    except Exception as e:
        st.error("Error al enviar el requerimiento.")
        st.exception(e)


def enviar_recepcion_a_gsheet(lista_recepcion_data):
    url = st.secrets.get("APPS_SCRIPT_RECEPCION_URL", "")

    if not url:
        st.warning(
            "No se configuró APPS_SCRIPT_RECEPCION_URL en secrets. "
            "La recepción NO se enviará a la hoja 'Requerimientos'."
        )
        return

    rows = []
    for rec_data in lista_recepcion_data:
        row = [rec_data.get(col, "") for col in RECEPCION_COLUMNS]
        rows.append(row)

    payload = {
        "rows": rows,
        "accion": "registrar_recepcion",  # por si lo usas en Apps Script
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)

        # Debug opcional:
        # st.markdown("#### Respuesta cruda de Apps Script (recepción – debug)")
        # st.code(resp.text, language="json")

        if resp.status_code != 200:
            st.error(
                f"No se pudo registrar la recepción. Código HTTP: {resp.status_code}"
            )
            return

        try:
            data = resp.json()
        except Exception as e:
            st.warning(
                "La respuesta de Apps Script (recepción) no es un JSON válido. "
                "Revisa el contenido crudo si activas el modo debug."
            )
            st.exception(e)
            return

        status = data.get("status")
        if status == "ok":
            # Solo mostramos 'Filas insertadas' si viene en el JSON
            inserted = data.get("inserted", None)
            if inserted is not None:
                st.success(
                    f"Recepción registrada correctamente. "
                    f"Filas insertadas: {inserted}."
                )
            else:
                st.success("Recepción registrada correctamente en Google Sheets.")
        else:
            st.warning(
                "Apps Script respondió pero con status distinto de 'ok'. "
                f"Respuesta: {data}"
            )

    except Exception as e:
        st.error("Error al enviar la recepción a Google Sheets.")
        st.exception(e)


def enviar_nuevo_producto_a_catalogo(nombre: str, categoria: str | None = None):
    url = st.secrets.get("APPS_SCRIPT_CATALOGO_URL", "")
    if not url:
        st.warning(
            "No se configuró APPS_SCRIPT_CATALOGO_URL en secrets. "
            "El nuevo producto NO se enviará al catálogo."
        )
        return

    if categoria is None or str(categoria).strip() == "":
        categoria = "Sin categoría"

    payload = {
        "accion": "nuevo_producto",
        "producto": nombre,
        "categoria": categoria,
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)

        st.markdown("#### Respuesta cruda de Apps Script (catálogo – debug)")
        st.code(resp.text, language="json")

        if resp.status_code != 200:
            st.error(
                f"No se pudo enviar el nuevo producto. Código HTTP: {resp.status_code}"
            )
            return

        try:
            data = resp.json()
        except Exception as e:
            st.warning(
                "La respuesta de Apps Script (catálogo) no es un JSON válido. "
                "Revisa el contenido mostrado arriba."
            )
            st.exception(e)
            return

        status = data.get("status")
        if status == "ok":
            if data.get("exists"):
                st.info(f"El producto '{nombre}' ya existe en el catálogo.")
            else:
                st.success(f"Producto '{nombre}' enviado y agregado al catálogo.")
        else:
            st.warning(
                "Apps Script de catálogo respondió con status distinto de 'ok'. "
                f"Respuesta: {data}"
            )

    except Exception as e:
        st.error("Error al enviar el nuevo producto al catálogo.")
        st.exception(e)


# --------------------------------------------------
# Selector de vista
# --------------------------------------------------
vista = st.sidebar.radio(
    "Selecciona el proceso:",
    (
        "📦 Requerimientos de producto",
        "📥 Recepción",
        "❓ FAQs",
    ),
)

# --------------------------------------------------
# VISTA FAQs
# --------------------------------------------------
if vista == "❓ FAQs":
    st.title("Carga de inventario")
    st.write(
        "Flujo:\n"
        "1) Descarga la plantilla, puedes encontrar el vínculo de descarga en la vista Carga de Inventario.\n"
        "2) Llenan la hoja **Movimientos_Inventario** en Excel/CSV, **las primeras 4 columnas quedan vacías**.\n"
        "3) Sube el archivo.\n"
        "4) Anota el folio generado para futuras consultas.\n"
    )

    st.title("Requerimientos de producto")
    st.write(
        "Flujo:\n"
        "1) Selecciona CECO Destino.\n"
        "2) Selecciona productos por categoría.\n"
        "3) Agrega las cantidades necesarias y observaciones.\n"
        "4) Una vez que confirmaste cantidades da clic en **Agregar producto al requerimiento**.\n"
        "5) Verifica los productos agregados y cantidades nuevamente, da clic en **Confirmar y enviar requerimiento**.\n"
        "6) Anota el folio generado para futuras consultas.\n"
    )

# --------------------------------------------------
# VISTA: Requerimientos de producto (con carrito)
# --------------------------------------------------
elif vista == "📦 Requerimientos de producto":
    st.header("📦 Requerimientos de producto")

    try:
        productos_df = load_catalogo_productos()
        st.success("Catálogo de productos cargado exitosamente.")
    except Exception as e:
        st.error(
            "No se pudo cargar el catálogo de productos desde la plantilla de inventario. "
            "Revisa que exista la hoja 'Catálogo'."
        )
        st.exception(e)
        st.stop()

    st.subheader("📝 Crear nuevo requerimiento (carrito de productos)")

    with st.container():
        col1, col2 = st.columns(2)

        opciones_ceco = [
            "Flautas Lamartine",
            "Burritos Masaryk",
            "Burritos Miyana",
            "Comisariato",
            "Waldos & Crispier",
            "Eventos",
        ]
        ceco_destino = col1.selectbox("CECO Destino", opciones_ceco)

        fecha_requerida = col2.date_input(
            "Fecha requerida (fecha de entrega)",
            value=date.today(),
        )

        st.markdown("### Producto a agregar al requerimiento")

        categorias_unicas = sorted(
            productos_df["Categoria"].dropna().astype(str).unique().tolist()
        )

        OPCION_TODAS = "--- Todas las categorías ---"
        categoria_sel = st.selectbox(
            "Categoría de producto",
            [OPCION_TODAS] + categorias_unicas,
            key="categoria_producto",
        )

        if categoria_sel == OPCION_TODAS:
            productos_filtrados = productos_df.copy()
        else:
            productos_filtrados = productos_df[
                productos_df["Categoria"] == categoria_sel
                ].copy()

        lista_productos = productos_filtrados["Producto"].dropna().unique().tolist()
        lista_productos = sorted(lista_productos)

        producto_sel = st.selectbox(
            "Producto",
            lista_productos,
            key="producto_seleccionado",
        )

        # Obtener datos del producto seleccionado
        fila_prod = productos_filtrados[productos_filtrados["Producto"] == producto_sel]
        if not fila_prod.empty:
            sku_prod = fila_prod.iloc[0].get("Referencia Interna", "")
            udm_prod = fila_prod.iloc[0].get("UdM de Compra", "pz")
            prov_prod = fila_prod.iloc[0].get("Proveedor", "")
            cat_prod = fila_prod.iloc[0].get("Categoria", "Sin categoría")
        else:
            sku_prod = ""
            udm_prod = "pz"
            prov_prod = ""
            cat_prod = "Sin categoría"

        col_cant, col_obs = st.columns(2)
        cantidad_req = col_cant.number_input(
            "Cantidad requerida",
            min_value=0.0,
            step=1.0,
            value=1.0,
            key="cantidad_req",
        )
        observaciones_req = col_obs.text_input(
            "Observaciones (opcional)",
            value="",
            key="obs_req",
        )

        if st.button("➕ Agregar producto al requerimiento"):
            if not producto_sel:
                st.error("Debes seleccionar un producto.")
            elif cantidad_req <= 0:
                st.error("La cantidad debe ser mayor a 0.")
            else:
                item = {
                    "INSUMO": producto_sel,
                    "UNIDAD DE MEDIDA": udm_prod,
                    "CANTIDAD": cantidad_req,
                    "Observaciones": observaciones_req,
                    "SKU": sku_prod,
                    "PROVEDOR": prov_prod,
                    "Categoria": cat_prod,
                }
                st.session_state["carrito_req"].append(item)
                st.success(f"Producto '{producto_sel}' agregado al carrito.")

    # ----- Mostrar carrito -----
    st.markdown("---")
    st.subheader("🛒 Carrito de requerimientos")

    if st.session_state["carrito_req"]:
        carrito_df = pd.DataFrame(st.session_state["carrito_req"])
        carrito_df["__idx__"] = range(len(carrito_df))

        # Agrupar por categoría si existe
        if "Categoria" in carrito_df.columns:
            categorias_orden = sorted(carrito_df["Categoria"].dropna().unique().tolist())

            for cat in categorias_orden:
                subset = carrito_df[carrito_df["Categoria"] == cat]
                st.markdown(f"#### 📂 {cat}")

                header_cols = st.columns([4, 2, 2, 4, 1])
                header_cols[0].markdown("**Producto**")
                header_cols[1].markdown("**Unidad**")
                header_cols[2].markdown("**Cantidad**")
                header_cols[3].markdown("**Observaciones**")
                header_cols[4].markdown("**Borrar**")

                for _, row in subset.iterrows():
                    c1, c2, c3, c4, c5_columns = st.columns([4, 2, 2, 4, 1])
                    c1.write(row.get("INSUMO", ""))
                    c2.write(row.get("UNIDAD DE MEDIDA", ""))
                    c3.write(row.get("CANTIDAD", ""))
                    c4.write(row.get("Observaciones", ""))

                    delete_key = f"del_{int(row['__idx__'])}"
                    if c5_columns.button("❌", key=delete_key):
                        st.session_state["carrito_req"].pop(int(row["__idx__"]))
                        st.rerun()
        else:
            header_cols = st.columns([4, 2, 2, 4, 1])
            header_cols[0].markdown("**Producto**")
            header_cols[1].markdown("**Unidad**")
            header_cols[2].markdown("**Cantidad**")
            header_cols[3].markdown("**Observaciones**")
            header_cols[4].markdown("**Borrar**")

            for _, row in carrito_df.iterrows():
                c1, c2, c3, c4, c5_columns = st.columns([4, 2, 2, 4, 1])
                c1.write(row.get("INSUMO", ""))
                c2.write(row.get("UNIDAD DE MEDIDA", ""))
                c3.write(row.get("CANTIDAD", ""))
                c4.write(row.get("Observaciones", ""))

                delete_key = f"del_{int(row['__idx__'])}"
                if c5_columns.button("❌", key=delete_key):
                    st.session_state["carrito_req"].pop(int(row["__idx__"]))
                    st.rerun()

        colc1, colc2 = st.columns(2)
        vaciar = colc1.button("🗑️ Vaciar carrito")
        send_req = colc2.button(
            "✅ Confirmar y enviar requerimiento", key="btn_send_req"
        )

        if vaciar:
            st.session_state["carrito_req"] = []
            st.info("Carrito vaciado.")

        # ----- Enviar requerimiento -----
        if send_req:
            errores = []

            tz = pytz.timezone("America/Mexico_City")
            hoy = datetime.now(tz).date()
            diferencia_dias = (fecha_requerida - hoy).days

            # Lead time mínimo de 4 días (excepto Flautas Lamartine)
            if ceco_destino != "Flautas Lamartine":
                if diferencia_dias < 4:
                    st.warning(
                        "NO ES POSIBLE GENERAR PEDIDOS CON UN TIEMPO MENOR A 4 DÍAS "
                        f"(hoy: {hoy.isoformat()}, fecha requerida: {fecha_requerida.isoformat()})."
                    )
                    errores.append(
                        "La *Fecha requerida* debe ser al menos 4 días después de la fecha actual."
                    )

            # No se permiten sábados ni domingos en la fecha requerida
            if fecha_requerida.weekday() >= 5:  # 5 = sábado, 6 = domingo
                errores.append(
                    "La *Fecha requerida* no puede ser sábado ni domingo. "
                    "Elige un día hábil (lunes a viernes)."
                )

            if not ceco_destino:
                errores.append("Debes seleccionar el *CECO destino*.")
            if not st.session_state["carrito_req"]:
                errores.append("El carrito está vacío. Agrega al menos un producto.")

            if errores:
                st.error("No se pudo enviar el requerimiento:")
                for e in errores:
                    st.write("-", e)
            else:
                folio_req, fecha_creacion, hora_creacion = generar_folio_requerimiento()
                st.info(f"Folio de requerimiento generado: **{folio_req}**")

                lista_req_data = []

                for item in st.session_state["carrito_req"]:
                    req_data = {
                        "FECHA DE PEDIDO": fecha_creacion,
                        "PROVEDOR": item.get("PROVEDOR", ""),
                        "INSUMO": item["INSUMO"],
                        "UNIDAD DE MEDIDA": item["UNIDAD DE MEDIDA"],
                        "COSTO UNIDAD": "",
                        "CANTIDAD": item["CANTIDAD"],
                        "COSTO TOTAL": "",
                        "FECHA DESEADA": fecha_requerida.isoformat(),
                        "OBSERVACIONES": item["Observaciones"],
                        "ESTATUS": "Pendiente",
                        "ID_REQ": folio_req,
                        "Hora": hora_creacion,
                        "CECO_DESTINO": ceco_destino,
                        "CATEGORIA": item.get("Categoria", "Sin categoría"),
                        "Fecha aproximada de entrega": fecha_requerida.isoformat(),
                        "SKU": item.get("SKU", ""),
                    }

                    lista_req_data.append(req_data)

                lista_req_data = sorted(
                    lista_req_data,
                    key=lambda x: (x.get("CATEGORIA", ""), x.get("INSUMO", "")),
                )

                enviar_requerimientos_a_gsheet(lista_req_data)
                st.session_state["carrito_req"] = []

    else:
        send_req = False

    # ----- Consulta estatus de requerimientos -----
    st.subheader("🔍 Consultar estatus de requerimientos")

    _, col_f2 = st.columns(2)
    filtro_folio = col_f2.text_input(
        "Buscar por folio (ID_REQ) (opcional, coincidencia exacta)",
        value="",
    )

    if st.button("🔄 Actualizar listado"):
        try:
            load_requerimientos_from_gsheet.clear()
            req_df = load_requerimientos_from_gsheet()

            if "ID_REQ" not in req_df.columns or "ESTATUS" not in req_df.columns:
                st.error(
                    "No pude encontrar columnas 'ID_REQ' y 'ESTATUS' en la hoja de requerimientos.\n\n"
                    f"Columnas leídas: {list(req_df.columns)}\n\n"
                    "Revisa que el CSV de requerimientos tenga esos encabezados en la fila 1."
                )
                st.stop()

            if "FECHA DE PEDIDO" in req_df.columns and "Hora" in req_df.columns:
                req_df_sorted = req_df.sort_values(
                    by=["FECHA DE PEDIDO", "Hora"], ascending=[True, True]
                )
            else:
                req_df_sorted = req_df.copy()

            if filtro_folio:
                mask = (
                        req_df_sorted["ID_REQ"].astype(str).str.lower()
                        == filtro_folio.lower()
                )
                df_filtrado = req_df_sorted[mask].copy()

                if df_filtrado.empty:
                    st.warning("No se encontró ningún requerimiento con ese ID_REQ.")
                    st.stop()
            else:
                df_filtrado = req_df_sorted

            agg_dict = {"ESTATUS": "last"}
            cols_resumen = ["ID_REQ", "ESTATUS"]

            if "FECHA DE PEDIDO" in df_filtrado.columns:
                agg_dict["FECHA DE PEDIDO"] = "last"
                cols_resumen.append("FECHA DE PEDIDO")
            if "FECHA DESEADA" in df_filtrado.columns:
                agg_dict["FECHA DESEADA"] = "last"
                cols_resumen.append("FECHA DESEADA")

            resumen = df_filtrado.groupby("ID_REQ", as_index=False).agg(agg_dict)

            st.markdown("### 📊 Resumen de requerimiento de compra")
            st.dataframe(
                resumen[cols_resumen].reset_index(drop=True),
                use_container_width=True,
                hide_index=True,
            )

            if filtro_folio:
                st.markdown(f"### 📄 Detalle de productos del folio: `{filtro_folio}`")
                detalle = df_filtrado.copy()

                cols_detalle = [
                    c
                    for c in [
                        "ID_REQ",
                        "INSUMO",
                        "UNIDAD DE MEDIDA",
                        "CANTIDAD",
                        "FECHA DESEADA"
                        if "FECHA DESEADA" in detalle.columns
                        else None,
                        "ESTATUS",
                        "OBSERVACIONES",
                    ]
                    if c is not None and c in detalle.columns
                ]

                st.dataframe(
                    detalle[cols_detalle].reset_index(drop=True),
                    use_container_width=True,
                    hide_index=True,
                )

        except Exception as e:
            st.error(
                "No se pudo cargar la hoja de requerimientos desde Google Sheets. "
                "Revisa REQUERIMIENTOS_CSV_URL en secrets y la publicación del archivo."
            )
            st.exception(e)

# --------------------------------------------------
# VISTA: Recepción de producto
# --------------------------------------------------
elif vista == "📥 Recepción":
    st.header("📥 Recepción de producto")

    st.markdown(
        "1) Consulta un requerimiento por folio **ID_REQ**.  \n"
        "2) Se cargará una tabla con los insumos del pedido.  \n"
        "3) En esa misma tabla, por **cada fila** captura: Fecha de recepción, Factura/Ticket, "
        "Recibió, Cantidad recibida, Temperatura, Calidad, Observaciones y fecha de caducidad.  \n"
        "4) Registra todo en la hoja de Google mediante un solo botón."
    )

    try:
        catalogo_df = load_catalogo_productos()
    except Exception:
        catalogo_df = pd.DataFrame()

    # ---------- 1) Buscar requerimiento por folio ----------
    col_buscar1, col_buscar2 = st.columns([2, 1])
    id_req_input = col_buscar1.text_input(
        "Folio de requerimiento (ID_REQ)",
        value=st.session_state.get("req_recepcion_id", ""),
        help="Es el mismo folio que se generó en Requerimientos (REQ-YYYYMMDD-HHMMSS).",
    )
    btn_buscar_req = col_buscar2.button("🔍 Buscar requerimiento")

    if btn_buscar_req:
        if not id_req_input.strip():
            st.error("Debes capturar un folio de requerimiento (ID_REQ).")
        else:
            try:
                # ✅ FIX #1: Limpiar cache antes de cargar para datos frescos
                load_requerimientos_from_gsheet.clear()
                req_df = load_requerimientos_from_gsheet()

                if "ID_REQ" not in req_df.columns:
                    st.error(
                        "No se encontró la columna 'ID_REQ' en la hoja de requerimientos. "
                        f"Columnas leídas: {list(req_df.columns)}"
                    )
                    st.stop()

                mask = req_df["ID_REQ"].astype(str).str.strip() == id_req_input.strip()
                df_req_folio = req_df[mask].copy()

                if df_req_folio.empty:
                    st.warning(
                        f"No se encontraron registros con el folio ID_REQ = '{id_req_input}'."
                    )
                    st.session_state["req_recepcion_df"] = None
                    st.session_state["req_recepcion_id"] = id_req_input.strip()
                else:
                    # ✅ FIX #6: Limpiar filas con INSUMO vacío o NaN
                    if "INSUMO" in df_req_folio.columns:
                        df_req_folio = df_req_folio[df_req_folio["INSUMO"].notna()].copy()
                        df_req_folio["INSUMO"] = df_req_folio["INSUMO"].astype(str).str.strip()
                        df_req_folio = df_req_folio[df_req_folio["INSUMO"] != ""]
                        df_req_folio = df_req_folio.sort_values("INSUMO")

                    # ✅ FIX #2: Convertir CANTIDAD a numérico
                    if "CANTIDAD" in df_req_folio.columns:
                        df_req_folio["CANTIDAD"] = pd.to_numeric(
                            df_req_folio["CANTIDAD"], errors="coerce"
                        ).fillna(0.0)

                    st.session_state["req_recepcion_df"] = df_req_folio
                    st.session_state["req_recepcion_id"] = id_req_input.strip()

                    # ✅ FIX #3: Incrementar versión del editor para forzar recreación
                    st.session_state["editor_version"] += 1

                    st.success("Requerimiento cargado correctamente.")

                    # ✅ FIX #5: Forzar rerun para evitar race conditions
                    st.rerun()

            except Exception as e:
                st.error(
                    "No se pudo cargar la hoja de requerimientos desde Google Sheets. "
                    "Revisa REQUERIMIENTOS_CSV_URL en secrets y la publicación del archivo."
                )
                st.exception(e)

    df_req_folio = st.session_state.get("req_recepcion_df", None)
    id_req_actual = st.session_state.get("req_recepcion_id", "")

    # ---------- 2) Mostrar detalle del requerimiento ----------
    if df_req_folio is not None and not df_req_folio.empty:
        st.markdown("### 🧾 Productos del requerimiento")

        cols_detalle_req = [
            c
            for c in [
                "INSUMO",
                "UNIDAD DE MEDIDA",
                "CANTIDAD",
                "FECHA DE PEDIDO" if "FECHA DE PEDIDO" in df_req_folio.columns else None,
                "FECHA DESEADA" if "FECHA DESEADA" in df_req_folio.columns else None,
                "CECO_DESTINO" if "CECO_DESTINO" in df_req_folio.columns else None,
            ]
            if c is not None and c in df_req_folio.columns
        ]

        st.dataframe(
            df_req_folio[cols_detalle_req].reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
        )

        # ---------- 3) Tabla editable: recepción por insumo (CON SOPORTE PARCIAL) ----------
        st.markdown("### 📦 Registro de recepción por insumo")

        if "INSUMO" not in df_req_folio.columns or "CANTIDAD" not in df_req_folio.columns:
            st.error(
                "La hoja de requerimientos debe tener columnas 'INSUMO' y 'CANTIDAD' "
                "para construir la tabla de recepción."
            )
        else:
            # ✅ NUEVO: Calcular pendientes considerando recepciones previas
            pendientes_df = calcular_pendientes_por_producto(id_req_actual, df_req_folio)

            # Mostrar resumen de estado
            total_po = pendientes_df["CANTIDAD PO"].sum()
            total_recibido = pendientes_df["CANTIDAD RECIBIDA TOTAL"].sum()
            total_pendiente = pendientes_df["CANTIDAD PENDIENTE"].sum()

            col_res1, col_res2, col_res3 = st.columns(3)
            col_res1.metric("📦 Total PO", f"{total_po:.0f}")
            col_res2.metric("✅ Ya Recibido", f"{total_recibido:.0f}")
            col_res3.metric("⏳ Pendiente", f"{total_pendiente:.0f}")

            # ✅ NUEVO: Mostrar historial de recepciones previas
            historial_df = obtener_historial_recepciones(id_req_actual)
            if not historial_df.empty:
                with st.expander("📋 Ver historial de recepciones anteriores", expanded=False):
                    # Columnas adaptadas a la hoja de Requerimientos
                    cols_hist = [c for c in [
                        "Folio Generado de Recepcion", "Fecha de recepción app", "INSUMO",
                        "CANTIDAD RECIBIDA", "CANTIDAD PENDIENTE", "Estatus Recepción",
                        "CALIDAD (OK / RECHAZO)", "OBSERVACIONES RECEPCIÓN", "RECIBIÓ"
                    ] if c in historial_df.columns]

                    if cols_hist:
                        st.dataframe(
                            historial_df[cols_hist].reset_index(drop=True),
                            use_container_width=True,
                            hide_index=True,
                        )
                    else:
                        st.dataframe(historial_df.reset_index(drop=True), use_container_width=True)

            # ✅ NUEVO: Opción para ver solo pendientes o todos
            mostrar_opcion = st.radio(
                "¿Qué productos mostrar?",
                options=["Solo pendientes", "Todos los productos"],
                horizontal=True,
                key="mostrar_productos_opcion"
            )

            if mostrar_opcion == "Solo pendientes":
                base_df = pendientes_df[pendientes_df["CANTIDAD PENDIENTE"] > 0].copy()
                if base_df.empty:
                    st.success("🎉 ¡Todos los productos de este requerimiento ya fueron recibidos!")
                    st.stop()
            else:
                base_df = pendientes_df.copy()

            # Preparar campos editables
            base_df["Fecha de recepción"] = date.today()
            base_df["FACTURA / TICKET"] = ""
            base_df["RECIBIÓ"] = ""
            base_df["CANTIDAD A RECIBIR"] = 0.0
            base_df["TEMP (°C)"] = 0.0
            base_df["CALIDAD (OK / RECHAZO)"] = "OK"
            base_df["OBSERVACIONES"] = ""
            base_df["fecha de caducidad"] = pd.NaT

            # Key único con versión para forzar recreación
            editor_key = f"editor_recepcion_{id_req_actual}_{st.session_state.get('editor_version', 0)}"

            # Editor con columnas mejoradas
            edited_df = st.data_editor(
                base_df,
                column_config={
                    "INSUMO": st.column_config.TextColumn(
                        "Producto",
                        disabled=True,
                    ),
                    "SKU": st.column_config.TextColumn(
                        "SKU",
                        disabled=True,
                    ),
                    "CANTIDAD PO": st.column_config.NumberColumn(
                        "Cantidad PO",
                        disabled=True,
                        help="Cantidad solicitada en el requerimiento original",
                    ),
                    "CANTIDAD RECIBIDA TOTAL": st.column_config.NumberColumn(
                        "Ya Recibido",
                        disabled=True,
                        help="Cantidad ya recibida en recepciones anteriores",
                    ),
                    "CANTIDAD PENDIENTE": st.column_config.NumberColumn(
                        "Pendiente",
                        disabled=True,
                        help="Cantidad que falta por recibir",
                    ),
                    "PROVEEDOR": st.column_config.TextColumn(
                        "Proveedor",
                        disabled=True,
                    ),
                    "Fecha de recepción": st.column_config.DateColumn(
                        "Fecha de recepción",
                        help="Fecha de esta recepción",
                    ),
                    "FACTURA / TICKET": st.column_config.TextColumn(
                        "Factura / Ticket",
                        help="Número de factura o ticket",
                    ),
                    "RECIBIÓ": st.column_config.TextColumn(
                        "Recibió",
                        help="Persona que recibe",
                    ),
                    "CANTIDAD A RECIBIR": st.column_config.NumberColumn(
                        "🆕 Cantidad a Recibir",
                        help="Cantidad que estás recibiendo AHORA (puede ser parcial)",
                        min_value=0.0,
                    ),
                    "TEMP (°C)": st.column_config.NumberColumn(
                        "Temp (°C)",
                        help="Temperatura al recibir (si aplica)",
                        min_value=-50.0,
                        max_value=100.0,
                        step=0.5,
                    ),
                    "CALIDAD (OK / RECHAZO)": st.column_config.SelectboxColumn(
                        "Calidad",
                        options=["OK", "RECHAZO"],
                        help="Indica si se acepta o rechaza",
                    ),
                    "OBSERVACIONES": st.column_config.TextColumn(
                        "Observaciones",
                        help="Obligatorio si hay rechazo",
                    ),
                    "fecha de caducidad": st.column_config.DateColumn(
                        "Fecha caducidad",
                        help="Fecha de caducidad del lote",
                    ),
                },
                num_rows="fixed",
                use_container_width=True,
                key=editor_key,
                column_order=[
                    "INSUMO", "SKU", "CANTIDAD PO", "CANTIDAD RECIBIDA TOTAL", "CANTIDAD PENDIENTE",
                    "PROVEEDOR", "Fecha de recepción", "FACTURA / TICKET", "RECIBIÓ",
                    "CANTIDAD A RECIBIR", "TEMP (°C)", "CALIDAD (OK / RECHAZO)", "OBSERVACIONES", "fecha de caducidad"
                ],
            )

            st.markdown(
                "> **💡 Tip:** Solo se enviarán los productos donde captures una **'Cantidad a Recibir' > 0**.  \n"
                "> Puedes hacer recepciones parciales y volver después a completar el resto."
            )

            # ✅ NUEVO: Mostrar resumen de lo que se va a enviar
            if edited_df is not None:
                df_a_enviar = edited_df[edited_df["CANTIDAD A RECIBIR"] > 0].copy()

                # Validar observaciones en rechazos y cantidades
                if not df_a_enviar.empty:
                    eps = 1e-6  # tolerancia para errores flotantes

                    for _, row in df_a_enviar.iterrows():
                        calidad = str(row.get("CALIDAD (OK / RECHAZO)", "OK") or "OK")
                        obs = str(row.get("OBSERVACIONES", "") or "").strip()

                        cant_recibir = float(row.get("CANTIDAD A RECIBIR", 0) or 0)
                        cant_pendiente = float(row.get("CANTIDAD PENDIENTE", 0) or 0)

                        if calidad == "RECHAZO" and obs == "":
                            errores.append(
                                f"El producto '{row.get('INSUMO', '')}' tiene RECHAZO pero no hay observaciones."
                            )

                        # ✅ Comparación robusta (NO falla por decimales)
                        if cant_recibir > cant_pendiente + eps:
                            errores.append(
                                f"El producto '{row.get('INSUMO', '')}' tiene cantidad a recibir ({cant_recibir:.2f}) "
                                f"mayor que la pendiente ({cant_pendiente:.2f})."
                            )

            # ---------- 4) Botón para registrar recepción ----------
            col_btn1, col_btn2 = st.columns(2)
            btn_limpiar = col_btn1.button("🧹 Limpiar tabla de recepción")
            btn_enviar_recep = col_btn2.button("✅ Registrar recepción parcial")

            if btn_limpiar:
                st.session_state["editor_version"] += 1
                st.rerun()

            if btn_enviar_recep:
                errores = []

                if not id_req_actual:
                    errores.append(
                        "No hay un ID de requerimiento cargado. "
                        "Vuelve a buscar el folio antes de registrar la recepción."
                    )

                if edited_df is None or edited_df.empty:
                    errores.append(
                        "La tabla de recepción está vacía. Verifica el requerimiento."
                    )

                # ✅ NUEVO: Filtrar solo productos con cantidad > 0
                df_a_enviar = edited_df[
                    edited_df["CANTIDAD A RECIBIR"] > 0].copy() if edited_df is not None else pd.DataFrame()

                if df_a_enviar.empty:
                    errores.append(
                        "No hay productos con 'Cantidad a Recibir' > 0. "
                        "Captura al menos un producto para enviar."
                    )

                # Validar observaciones en rechazos y cantidades
                if not df_a_enviar.empty:
                    for _, row in df_a_enviar.iterrows():
                        calidad = str(row.get("CALIDAD (OK / RECHAZO)", "OK") or "OK")
                        obs = str(row.get("OBSERVACIONES", "") or "").strip()

                        if calidad == "RECHAZO" and obs == "":
                            errores.append(
                                f"El producto '{row.get('INSUMO', '')}' tiene RECHAZO "
                                "pero no hay observaciones."
                            )

                        # Validar que no exceda pendiente
                        cant_recibir_r = round(cant_recibir, 2)
                        cant_pendiente_r = round(cant_pendiente, 2)

                        if cant_recibir_r > cant_pendiente_r:
                            errores.append(
                                f"El producto '{row.get('INSUMO', '')}' tiene cantidad a recibir ({cant_recibir_r:.2f}) "
                                f"mayor que la pendiente ({cant_pendiente_r:.2f})."
                            )



                if errores:
                    st.error("No se pudo registrar la recepción:")
                    for e in errores:
                        st.write("•", e)
                else:
                    folio_recep, fecha_folio, hora_folio = generar_folio_recepcion()
                    st.info(
                        f"**Folio de recepción:** {folio_recep}  \n"
                        f"**Fecha:** {fecha_folio} | **Hora:** {hora_folio}"
                    )

                    lista_recepcion_data = []
                    for _, row in df_a_enviar.iterrows():
                        cant_po = float(row.get("CANTIDAD PO", 0) or 0)
                        cant_rec = float(row.get("CANTIDAD A RECIBIR", 0) or 0)
                        obs = str(row.get("OBSERVACIONES", "") or "")

                        # Fecha de recepción
                        fecha_linea = row.get("Fecha de recepción", date.today())
                        if hasattr(fecha_linea, "isoformat"):
                            fecha_str = fecha_linea.isoformat()
                        else:
                            fecha_str = str(fecha_linea)

                        # Fecha de caducidad
                        fecha_cad = row.get("fecha de caducidad", None)
                        if isinstance(fecha_cad, (list, tuple)):
                            fecha_cad = fecha_cad[0] if fecha_cad else None

                        if pd.isna(fecha_cad):
                            fecha_cad_str = ""
                        elif fecha_cad and hasattr(fecha_cad, "isoformat"):
                            fecha_cad_str = fecha_cad.isoformat()
                        else:
                            fecha_cad_str = str(fecha_cad) if fecha_cad else ""

                        rec_data = {
                            "Fecha de recepción": fecha_str,
                            "PROVEEDOR": row.get("PROVEEDOR", ""),
                            "FACTURA / TICKET": row.get("FACTURA / TICKET", ""),
                            "SKU": row.get("SKU", ""),
                            "PRODUCTO": row.get("INSUMO", ""),
                            "UNIDAD DE MEDIDA": "pz",
                            "CANTIDAD PO": cant_po,
                            "CANTIDAD RECIBIDA": cant_rec,
                            "TEMP (°C)": float(row.get("TEMP (°C)", 0) or 0),
                            "CALIDAD (OK / RECHAZO)": row.get("CALIDAD (OK / RECHAZO)", "OK"),
                            "OBSERVACIONES": obs,
                            "RECIBIÓ": row.get("RECIBIÓ", ""),
                            "FOLIO": "",
                            "APROBÓ": "",
                            "ID DE REQUERIMIENTO AL QUE CORRESPONDE": id_req_actual,
                            "Folio Generado de Recepcion": folio_recep,
                            "fecha de caducidad": fecha_cad_str,
                        }
                        lista_recepcion_data.append(rec_data)

                    if lista_recepcion_data:
                        enviar_recepcion_a_gsheet(lista_recepcion_data)

                        # Limpiar para mostrar datos actualizados
                        st.session_state["editor_version"] += 1
                        st.success(
                            f"✅ Se registraron {len(lista_recepcion_data)} producto(s). "
                            "Recargando datos actualizados..."
                        )

                        # Dar tiempo para que Google Sheets procese
                        import time

                        time.sleep(1.5)
                        st.rerun()


    else:
        st.info(
            "Busca primero un folio de requerimiento (ID_REQ) para poder registrar la recepción."
        )

    # ---------- 5) Consulta de pendientes por requerimiento ----------
    st.markdown("---")
    st.markdown("### 🔍 Consulta de pendientes por requerimiento")

    id_req_pend = st.text_input(
        "Folio de requerimiento (ID_REQ) para ver productos pendientes",
        key="id_req_pendientes",
        help="Ejemplo: REQ-20251202-153045",
    )

    if st.button("Calcular pendientes", key="btn_calc_pendientes"):
        if not id_req_pend.strip():
            st.error("Debes capturar un folio de requerimiento (ID_REQ).")
        else:
            try:
                req_df = load_requerimientos_from_gsheet()
                req_df.columns = req_df.columns.astype(str).str.strip()

                if "ID_REQ" not in req_df.columns:
                    st.error(
                        "La hoja de Requerimientos no tiene la columna 'ID_REQ'. "
                        f"Columnas leídas: {list(req_df.columns)}"
                    )
                    st.stop()

                # Filtrar por folio
                req_folio = req_df[
                    req_df["ID_REQ"].astype(str).str.strip() == id_req_pend.strip()
                    ].copy()

                if req_folio.empty:
                    st.warning(
                        f"No se encontraron productos para el ID_REQ = '{id_req_pend}'."
                    )
                    st.stop()

                # Columna de producto
                if "INSUMO" in req_folio.columns:
                    col_prod_req = "INSUMO"
                elif "PRODUCTO" in req_folio.columns:
                    col_prod_req = "PRODUCTO"
                else:
                    st.error(
                        "No se encontró una columna de producto ('INSUMO' o 'PRODUCTO') "
                        "en la hoja de Requerimientos."
                    )
                    st.stop()

                # Localizar columna 'CANTIDAD PENDIENTE'
                col_cant_pend = None
                for c in req_folio.columns:
                    if norm(c) == "cantidadpendiente":
                        col_cant_pend = c
                        break

                if col_cant_pend is None:
                    st.error(
                        "No se encontró la columna de 'CANTIDAD PENDIENTE' "
                        "en la hoja de Requerimientos. "
                        f"Columnas leídas: {list(req_folio.columns)}"
                    )
                    st.stop()

                # A número
                req_folio[col_cant_pend] = pd.to_numeric(
                    req_folio[col_cant_pend], errors="coerce"
                ).fillna(0.0)

                # Solo filas con pendiente > 0
                req_pend = req_folio[req_folio[col_cant_pend] > 0].copy()

                if req_pend.empty:
                    st.info(
                        f"El requerimiento `{id_req_pend}` no tiene productos pendientes. 🎉"
                    )
                    st.stop()

                # Versión simple: filas con pendiente > 0
                cols_base = [col_prod_req, col_cant_pend]
                if "SKU" in req_pend.columns:
                    cols_base.insert(1, "SKU")

                pend_df = req_pend[cols_base].copy()

                rename_map = {col_prod_req: "PRODUCTO", col_cant_pend: "PENDIENTE"}
                pend_df = pend_df.rename(columns=rename_map)

                pend_df["PENDIENTE"] = pd.to_numeric(
                    pend_df["PENDIENTE"], errors="coerce"
                ).fillna(0.0)
                pend_df = pend_df[pend_df["PENDIENTE"] > 0]

                pend_df = pend_df.sort_values("PENDIENTE", ascending=False)

                if "SKU" in pend_df.columns:
                    cols_mostrar = ["SKU", "PRODUCTO", "PENDIENTE"]
                else:
                    cols_mostrar = ["PRODUCTO", "PENDIENTE"]

                st.markdown(
                    f"#### Resultado de pendientes para ID_REQ: `{id_req_pend}`"
                )
                st.dataframe(
                    pend_df[cols_mostrar].reset_index(drop=True),
                    use_container_width=True,
                    hide_index=True,
                )

                total_pend = pend_df["PENDIENTE"].sum()

                st.info(
                    f"**Resumen del requerimiento**  \n"
                    f"- Cantidad pendiente total: **{total_pend:.2f}**"
                )

            except Exception as e:
                st.error("Ocurrió un error al calcular los pendientes.")
                st.exception(e)
