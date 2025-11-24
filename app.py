import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime, date
import pytz
import os
import requests


LOGO_URL = "https://raw.githubusercontent.com/apalma-hps/inventario_streamlit/c773df92eb1036c7f4d9446462f3b8472b4eee29/20250625_1445_Neon%20Diner%20Night_remix_01jymd8rw4fed8atev6x9n3757.png"


# --------------------------------------------------
# Configuración básica de la página
# --------------------------------------------------
st.set_page_config(
    page_title="Inventario – Movimientos",
    page_icon=LOGO_URL,   # ahora usa tu logo real
    layout="wide"
)
# --------------------------------------------------
# THEME VISUAL A PARTIR DE LA IMAGEN DEL LOGO
# --------------------------------------------------
st.markdown("""
<style>

    /* Fondo general */
    .stApp {
        background-color: #060708 !important;
        color: #F4D38C !important;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0B0C0D !important;
        border-right: 1px solid #1d1d1d !important;
    }

    /* Títulos */
    h1, h2, h3, .stMarkdown h1, .stMarkdown h2 {
        color: #E03A2A !important;  /* rojo Hungry */
        font-weight: 700 !important;
    }

    /* Subtítulos */
    h4, h5 {
        color: #F4D38C !important;
    }

    /* Enlaces */
    a {
        color: #47FF8A !important;  /* verde neón */
        text-decoration: none !important;
    }
    a:hover {
        color: #74FFAF !important;
        text-decoration: underline !important;
    }

    /* Botones */
    button[kind="primary"] {
        background-color: #E03A2A !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
    }
    button[kind="primary"]:hover {
        background-color: #FF3B30 !important;
    }

    /* Inputs */
    .stTextInput > div > input,
    .stNumberInput input,
    textarea,
    select {
        background-color: #0F1011 !important;
        color: #F4D38C !important;
        border: 1px solid #E03A2A55 !important;
        border-radius: 6px !important;
    }

    /* Tablas */
    .dataframe {
        background-color: #0F1011 !important;
        color: #F4D38C !important;
        border-radius: 8px !important;
    }

    /* widgets internos */
    div[data-baseweb="select"] > div {
        background-color: #0F1011 !important;
        color: #F4D38C !important;
    }

    /* Mensajes success / error / warning */
    .stSuccess {
        background-color: #113d23 !important;
        color: #47FF8A !important;
        border-left: 4px solid #47FF8A !important;
    }
    .stError {
        background-color: #3d1111 !important;
        color: #FF3B30 !important;
        border-left: 4px solid #FF3B30 !important;
    }
    .stWarning {
        background-color: #3d2d11 !important;
        color: #F4D38C !important;
        border-left: 4px solid #F4D38C !important;
    }

</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# Encabezado con logo desde Google Drive
# --------------------------------------------------

st.markdown(
    f"""
    <div style="display:flex; align-items:center; gap:20px; margin-top:10px; margin-bottom:25px;">
        <img src="{LOGO_URL}" 
             style="
                width:120px; 
                height:120px; 
                object-fit:cover; 
                border-radius:50%; 
                box-shadow: 0 2px 6px rgba(0,0,0,0.15);
             "/>
        <h1 style="
            font-size: 2.1rem; 
            font-weight:700; 
            margin:0; 
            padding:0;
        ">
            Sistema de Gestión de Inventario y Requerimientos
        </h1>
    </div>
    """,
    unsafe_allow_html=True
)

# --------------------------------------------------
# URL de la plantilla de inventario (misma que usas para descarga)
# --------------------------------------------------
PLANTILLA_INVENTARIO_XLSX_URL = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vQ4Q30Ldblb-_bxRPugOXBCGU97CrsHozkf0conSHypwdVruRtH9UNXeT2D9mdu8XfDLknMk1UH2UBs/"
    "pub?output=xlsx"
)

# --------------------------------------------------
# Columnas que el USUARIO debe llenar en Movimientos_Inventario
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

# --------------------------------------------------
# Columnas en la hoja de Requerimientos (consolidado)
# --------------------------------------------------
REQUERIMIENTOS_COLUMNS = [
    "FECHA DE PEDIDO",
    "PROVEDOR",
    "INSUMO",
    "UNIDAD DE MEDIDA",
    "COSTO UNIDAD",
    "CANTIDAD",
    "COSTO TOTAL",
    "FECHA DE RECEPCIÓN",
    "FACTURA",
    "OBSERVACIONES",
    "ESTATUS",
    "ID_REQ",
    "Fecha",
    "Hora",
    "CECO_DESTINO",
    "CATEGORIA",
]


# --------------------------------------------------
# Inicializar session_state
# --------------------------------------------------
if "ultimo_inventario_df" not in st.session_state:
    st.session_state["ultimo_inventario_df"] = None
if "ultimo_inventario_folio" not in st.session_state:
    st.session_state["ultimo_inventario_folio"] = None
if "ultimo_inventario_fecha" not in st.session_state:
    st.session_state["ultimo_inventario_fecha"] = None
if "ultimo_inventario_hora" not in st.session_state:
    st.session_state["ultimo_inventario_hora"] = None

# carrito de productos para el requerimiento actual
if "carrito_req" not in st.session_state:
    st.session_state["carrito_req"] = []  # lista de dicts {INSUMO, CANTIDAD, UNIDAD, Factura, Observaciones}


# --------------------------------------------------
# Funciones auxiliares – Inventario
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
            f"Tipo de archivo no soportado: .{ext}. "
            "Usa archivos Excel (.xlsx, .xls) o CSV."
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


def generar_folio_inventario() -> (str, str, str):
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
            "No se configuró APPS_SCRIPT_CONSOLIDADO_URL en secrets. "
            "No se enviará nada al consolidado."
        )
        return

    df_json = df.copy()

    def to_jsonable(x):
        if isinstance(x, (pd.Timestamp, datetime, date)):
            return x.isoformat()
        return x

    df_json = df_json.applymap(to_jsonable)
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
# Funciones auxiliares – Catálogo y Requerimientos
# --------------------------------------------------

@st.cache_data
def load_catalogo_productos() -> pd.DataFrame:
    df = pd.read_excel(
        PLANTILLA_INVENTARIO_XLSX_URL,
        sheet_name="Catalogo_Productos"
    )

    df.columns = df.columns.astype(str).str.strip()

    if "Producto" not in df.columns:
        raise ValueError("La hoja Catalogo_Productos no contiene la columna 'Producto'.")

    # Usar columnas reales del catálogo
    if "Categoria" in df.columns:
        df = df[["Categoria", "Producto"]].copy()
    else:
        df = df[["Producto"]].copy()
        df["Categoria"] = "Sin categoría"

    df = df[df["Producto"].notna()]

    df["Producto"] = df["Producto"].astype(str).str.strip()
    df["Categoria"] = df["Categoria"].astype(str).str.strip()

    df = df[
        (df["Producto"] != "") &
        (df["Producto"].str.lower() != "nan")
    ].reset_index(drop=True)

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

    # Normalizar y renombrar columnas clave
    def norm(s: str) -> str:
        return (
            str(s)
            .strip()
            .lower()
            .replace(" ", "")
            .replace("_", "")
        )

    rename_map = {}
    for col in df.columns:
        n = norm(col)
        if n == "idreq":
            rename_map[col] = "ID_REQ"
        elif n == "estatus":
            rename_map[col] = "ESTATUS"
        elif n == "fechadepedido":
            rename_map[col] = "FECHA DE PEDIDO"
        elif n in ("fechaderecepcion", "fechaderecepción"):
            rename_map[col] = "FECHA DE RECEPCIÓN"


    df = df.rename(columns=rename_map)
    df.columns = df.columns.astype(str).str.strip()

    return df


def generar_folio_requerimiento() -> (str, str, str):
    tz = pytz.timezone("America/Mexico_City")
    ahora = datetime.now(tz)
    folio = ahora.strftime("REQ-%Y%m%d-%H%M%S")
    fecha = ahora.date().isoformat()
    hora = ahora.strftime("%H:%M:%S")
    return folio, fecha, hora


def enviar_requerimientos_a_gsheet(lista_req_data):
    """
    Envía una lista de dicts (varios productos) al Apps Script de Requerimientos.
    """
    url = st.secrets.get("APPS_SCRIPT_REQUERIMIENTOS_URL", "")

    if not url:
        st.warning(
            "No se configuró APPS_SCRIPT_REQUERIMIENTOS_URL en secrets. "
            "No se enviarán los requerimientos."
        )
        return

    rows = []
    for req_data in lista_req_data:
        row = [req_data.get(col, "") for col in REQUERIMIENTOS_COLUMNS]
        rows.append(row)

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
                    f"Requerimiento enviado y registrado. "
                    f"Filas insertadas: {data.get('inserted', 'desconocido')}."
                )
            else:
                st.warning(
                    "Se recibió respuesta de Apps Script pero con estado distinto de 'ok'. "
                    f"Respuesta: {data}"
                )
        else:
            st.error(
                f"No se pudo enviar el requerimiento. Código HTTP: {resp.status_code}"
            )
    except Exception as e:
        st.error("Error al enviar el requerimiento.")
        st.exception(e)


def enviar_nuevo_producto_a_catalogo(nombre: str):
    """
    Envía un nuevo producto para que Apps Script lo inserte
    en la hoja Catalogo_Productos (solo columna Producto).
    """
    url = st.secrets.get("APPS_SCRIPT_CATALOGO_URL", "")
    if not url:
        st.warning(
            "No se configuró APPS_SCRIPT_CATALOGO_URL en secrets. "
            "El nuevo producto NO se enviará al catálogo."
        )
        return

    payload = {
        "accion": "nuevo_producto",
        "producto": nombre,
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            st.success("Nuevo producto enviado para agregarlo al catálogo.")
        else:
            st.error(
                f"No se pudo enviar el nuevo producto. Código HTTP: {resp.status_code}"
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
       # "📥 Carga de Inventario",
       # "📊 Consulta último inventario cargado",
        "📨 Requerimientos de producto",
        "❓ FAQs",

    )
)
# --------------------------------------------------
# VISTA FAQs
# --------------------------------------------------
if vista == "❓ FAQs":

    st.title("Carga de inventario")

    st.write(
        "Flujo:\n"
        "1) Descarga la plantilla, puedes encontrar el vínculo de descarga en la vista Carga de Inventario.\n"
        "2) Llenan la hoja **Movimientos_Inventario** en Excel/CSV, ** La primeras 4 columnas quedan vacías**.\n"
        "3) Sube el archivo.\n"
        "4) Anota el folio generado para futuras consultas.\n"

    )

    st.title("Requerimientos de producto")

    st.write(
        "Flujo:\n"
        "1) Selecciona CECO Destino.\n"
        "2) Selecciona productos por categoría.\n"
        "3) Agrega las cantidades necesarias y observaciones.\n"
        "4) Una vez que confirmaste cantidades da clíck en **agregar producto al requerimiento**.\n"
        "5) Verifica los productos agregados y cantidades nuevamente, da clíck en ** confirmar y enviar requerimiento**.\n"
        "6) Anota el folio generado para futuras consultas.\n"

    )


# ---------




# --------------------------------------------------
# VISTA 1: Carga de inventario
# --------------------------------------------------
if vista == "📥 Carga de Inventario":
    st.header("📥 Carga de Inventario")

    st.subheader("1. Estructura base desde Google Sheets (solo lectura)")
    try:
        plantilla_gsheet_df = load_movimientos_template_from_gsheet()
        st.success("Plantilla cargada correctamente desde Google Sheets (solo headers).")
        with st.expander("Ver columnas detectadas en Movimientos_Inventario"):
            st.dataframe(plantilla_gsheet_df, use_container_width=True)
    except Exception as e:
        st.error(
            "No se pudo cargar la plantilla desde Google Sheets. "
            "Revisa la URL en secrets y los permisos/publicación de la hoja."
        )
        st.exception(e)
        st.stop()

    st.subheader("2. Descargar plantilla de inventario")
    st.write(
        "Descarga la plantilla . "
        "Incluye la hoja **Movimientos_Inventario** y **Catalogo_Productos**."
    )
    st.markdown(
        f"[⬇️ Descargar plantilla de inventario (Excel con productos y fórmulas)]({PLANTILLA_INVENTARIO_XLSX_URL})",
        unsafe_allow_html=True
    )

    st.subheader("3. Subir archivo con movimientos llenos y procesar")
    uploaded_file = st.file_uploader(
        "Sube tu archivo de movimientos (basado en la plantilla – Excel o CSV)",
        type=["xlsx", "xls", "csv"]
    )

    if uploaded_file is not None:
        st.write(f"Archivo cargado: **{uploaded_file.name}**")
        try:
            mov_df = leer_archivo_movimientos(uploaded_file)
            st.markdown("### Vista previa del archivo cargado (primeras filas)")
            st.dataframe(mov_df.head(), use_container_width=True)

            mov_df = validar_y_ordenar_columnas(mov_df)

            cantidades = pd.to_numeric(mov_df["Cantidad"], errors="coerce").fillna(0)
            filtrado_df = mov_df[cantidades > 0].copy()

            st.write(f"Filas con **Cantidad > 0**: **{len(filtrado_df)}**")

            if len(filtrado_df) > 0:
                folio, fecha, hora = generar_folio_inventario()
                filtrado_df = agregar_campos_sistema(filtrado_df, folio, fecha, hora)

                st.markdown("### Movimientos filtrados (solo con Cantidad > 0)")
                st.dataframe(filtrado_df, use_container_width=True)

                st.info(
                    f"Folio de inventario generado (ID de la carga): **{folio}**\n\n"
                    f"Fecha de carga: **{fecha}**  \n"
                    f"Hora de carga: **{hora}**"
                )

                st.session_state["ultimo_inventario_df"] = filtrado_df
                st.session_state["ultimo_inventario_folio"] = folio
                st.session_state["ultimo_inventario_fecha"] = fecha
                st.session_state["ultimo_inventario_hora"] = hora

                enviar_a_consolidado(filtrado_df)

                resultado_excel = df_to_excel_bytes(
                    filtrado_df,
                    sheet_name="Movimientos_Procesados"
                )

                st.download_button(
                    label="⬇️ Descargar movimientos procesados (Excel consolidado)",
                    data=resultado_excel,
                    file_name=f"movimientos_inventario_{folio}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning(
                    "No se encontraron filas con **Cantidad > 0**. "
                    "Revisa que hayas capturado cantidades en la columna 'Cantidad'."
                )

        except Exception as e:
            st.error("Ocurrió un error al leer o procesar el archivo subido.")
            st.exception(e)

# --------------------------------------------------
# VISTA 2: Último inventario cargado
# --------------------------------------------------
elif vista == "📊 Consulta último inventario cargado":
    st.header("📊 Consulta último inventario cargado")

    ultimo_df = st.session_state["ultimo_inventario_df"]
    folio = st.session_state["ultimo_inventario_folio"]
    fecha = st.session_state["ultimo_inventario_fecha"]
    hora = st.session_state["ultimo_inventario_hora"]

    if ultimo_df is None:
        st.warning(
            "Aún no se ha cargado ningún inventario en esta sesión.\n\n"
            "Ve a la vista **'📥 Carga de inventario'**, procesa un archivo "
            "y luego regresa aquí para ver el último inventario consolidado."
        )
    else:
        st.info(
            f"**Folio de inventario (ID de la carga):** {folio}\n\n"
            f"**Fecha de carga:** {fecha}  \n"
            f"**Hora de carga:** {hora}  \n"
            f"**Registros:** {len(ultimo_df)}"
        )

        st.markdown("### Detalle del último inventario consolidado")
        st.dataframe(ultimo_df, use_container_width=True)

        with st.expander("Ver resumen por SKU (suma de Cantidad)"):
            resumen_sku = (
                ultimo_df
                .groupby(["SKU", "Producto"], as_index=False)["Cantidad"]
                .sum()
                .sort_values("Cantidad", ascending=False)
            )
            st.dataframe(resumen_sku, use_container_width=True)

        resultado_excel = df_to_excel_bytes(
            ultimo_df,
            sheet_name="Ultimo_Inventario"
        )

        st.download_button(
            label="⬇️ Descargar último inventario (Excel)",
            data=resultado_excel,
            file_name=f"ultimo_inventario_{folio}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# --------------------------------------------------
# VISTA 3: Requerimientos de producto (con carrito multi-producto)
# --------------------------------------------------
elif vista == "📨 Requerimientos de producto":
    st.header("📨 Requerimientos de producto")

    # ---------- 1) Catálogo de productos ----------
    try:
        productos_df = load_catalogo_productos()
        st.success(
           "Catálogo de productos"
            " cargado exitosamente."
        )

        # Ya no mostramos el catálogo completo
        # with st.expander("Ver catálogo completo de productos"):
        #     st.dataframe(productos_df, use_container_width=True)

    except Exception as e:
        st.error(
            "No se pudo cargar el catálogo de productos desde la plantilla de inventario. "
            "Revisa que exista la hoja 'Catalogo_Productos'."
        )
        st.exception(e)
        st.stop()

    # ---------- 2) Formulario de captura (cabecera + línea de producto) ----------
    st.subheader("📝 Crear nuevo requerimiento (carrito de productos)")

    # Usamos un container en vez de st.form para que los filtros sean reactivos
    with st.container():
        col1, col2 = st.columns(2)

        # CECO destino como lista fija
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
            value=date.today()
        )

        st.markdown("### Producto a agregar al requerimiento")

        # --- Categoría (reactiva) ---
        categorias_unicas = sorted(
            productos_df["Categoria"].dropna().astype(str).unique().tolist()
        )

        OPCION_TODAS = "--- Todas las categorías ---"
        categoria_sel = st.selectbox(
            "Categoría de producto",
            [OPCION_TODAS] + categorias_unicas,
            key="categoria_producto"
        )

        if categoria_sel == OPCION_TODAS:
            df_filtrado_cat = productos_df.copy()
        else:
            df_filtrado_cat = productos_df[
                productos_df["Categoria"] == categoria_sel
            ].copy()

        productos_unicos = sorted(
            df_filtrado_cat["Producto"].dropna().astype(str).unique().tolist()
        )

        OPCION_OTRO = "Otro producto (no está en el catálogo)"
        opciones_productos = ["--- Selecciona un producto ---"] + productos_unicos + [OPCION_OTRO]

        producto_sel = st.selectbox(
            "Producto",
            opciones_productos,
            key="producto_sel"
        )

        es_nuevo = False
        producto_final = None

        if producto_sel == OPCION_OTRO:
            es_nuevo = True
            st.info("Captura datos para agregar un nuevo producto al catálogo.")
            st.warning(
                "⚠️ Este producto **no está en el catálogo**. "
                "Es obligatorio **justificar la compra** en el campo *Observaciones* para poder agregarlo."
            )
            producto_final = st.text_input("Nombre del nuevo producto")
        else:
            es_nuevo = False
            producto_final = (
                None
                if producto_sel == "--- Selecciona un producto ---"
                else producto_sel
            )

        cantidad = st.number_input(
            "Cantidad requerida para este producto",
            min_value=0.0,
            step=1.0
        )

        #factura = st.text_input("Factura (si aplica, para este producto)")
        observaciones = st.text_area("Observaciones (para este producto)")

        colb1, _ = st.columns(2)
        add_line = colb1.button("➕ Agregar producto al requerimiento", key="btn_add_line")
        # El botón de enviar lo movemos abajo, junto al de vaciar carrito
        send_req = False  # lo definimos aquí para tenerlo siempre declarado

    # ---------- 2.a) Manejar botón: Agregar producto al carrito ----------
    if add_line:
        errores = []

        if producto_final is None or producto_final == "":
            errores.append("Debes seleccionar un producto o capturar uno nuevo.")

        if cantidad <= 0:
            errores.append("La *Cantidad requerida* debe ser mayor a 0.")

        # 🔴 Regla nueva: si es un producto nuevo, Observaciones es obligatorio
        if es_nuevo and (not observaciones or not observaciones.strip()):
            errores.append(
                "Para productos que **no están en el catálogo** es obligatorio "
                "justificar la compra en el campo *Observaciones*."
            )

        if errores:
            st.error("No se pudo agregar el producto al requerimiento:")
            for e in errores:
                st.write("-", e)
        else:
            # Determinar categoría del producto (lo que ya tenías)
            if es_nuevo:
                if categoria_sel != OPCION_TODAS:
                    categoria_item = categoria_sel
                else:
                    categoria_item = "Sin categoría"
                if producto_final:
                    enviar_nuevo_producto_a_catalogo(producto_final)
            else:
                mask = (
                        productos_df["Producto"]
                        .astype(str)
                        .str.strip()
                        == str(producto_final).strip()
                )
                if mask.any():
                    categoria_item = productos_df.loc[mask, "Categoria"].iloc[0]
                else:
                    categoria_item = (
                        categoria_sel if categoria_sel != OPCION_TODAS else "Sin categoría"
                    )

            item = {
                "INSUMO": producto_final,
                "UNIDAD DE MEDIDA": "pz",
                "CANTIDAD": cantidad,
                "Observaciones": observaciones,
                "Categoria": categoria_item,
            }
            st.session_state["carrito_req"].append(item)
            st.success(
                f"Producto agregado al requerimiento: {producto_final} "
                f"(Cantidad: {cantidad}, Categoría: {categoria_item})"
            )


    # ---------- Vista del carrito actual ----------
    if st.session_state["carrito_req"]:
        st.markdown("### 🛒 Carrito de productos del requerimiento actual")

        carrito_df = pd.DataFrame(st.session_state["carrito_req"])

        if "Categoria" in carrito_df.columns:
            # Ordenamos por categoría para que se vea agrupado
            categorias_orden = (
                carrito_df["Categoria"]
                .fillna("Sin categoría")
                .astype(str)
                .unique()
                .tolist()
            )

            for cat in categorias_orden:
                subset = carrito_df[carrito_df["Categoria"] == cat]
                st.markdown(f"#### 📂 {cat}")
                st.dataframe(
                    subset.drop(columns=["Categoria"]),
                    use_container_width=True,
                )
        else:
            st.dataframe(carrito_df, use_container_width=True)

        colc1, colc2 = st.columns(2)
        vaciar = colc1.button("🗑️ Vaciar carrito")
        send_req = colc2.button("✅ Confirmar y enviar requerimiento", key="btn_send_req")

        if vaciar:
            st.session_state["carrito_req"] = []
            st.info("Carrito vaciado.")

        # ---------- Confirmar y enviar requerimiento ----------
        if send_req:
            errores = []
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
                proveedor = ""  # de momento vacío

                for item in st.session_state["carrito_req"]:
                    req_data = {
                        "FECHA DE PEDIDO": fecha_creacion,
                        "PROVEDOR": proveedor,
                        "INSUMO": item["INSUMO"],
                        "UNIDAD DE MEDIDA": item["UNIDAD DE MEDIDA"],
                        "COSTO UNIDAD": "",  # lo podrás rellenar después en la hoja
                        "CANTIDAD": item["CANTIDAD"],
                        "COSTO TOTAL": "",  # idem
                        "FECHA DE RECEPCIÓN": fecha_requerida.isoformat(),
                        "FACTURA": "",  # ya no se captura en el formulario
                        "OBSERVACIONES": item["Observaciones"],
                        "ESTATUS": "Pendiente",
                        "ID_REQ": folio_req,
                        "Fecha": fecha_creacion,
                        "Hora": hora_creacion,
                        "CECO_DESTINO": ceco_destino,
                        "CATEGORIA": item.get("Categoria", "Sin categoría"),
                    }
                    lista_req_data.append(req_data)

                # Opcional pero recomendable: ordenar por categoría y producto
                lista_req_data = sorted(
                    lista_req_data,
                    key=lambda x: (x.get("CATEGORIA", ""), x.get("INSUMO", ""))
                )

                enviar_requerimientos_a_gsheet(lista_req_data)
                st.session_state["carrito_req"] = []

    else:
        # Si no hay carrito, no mostramos botones
        send_req = False

    # ---------- 3) Consulta de estatus de requerimientos ----------
    st.subheader("🔍 Consultar estatus de requerimientos")

    col_f1, col_f2 = st.columns(2)
    filtro_folio = col_f2.text_input(
        "Buscar por folio (ID_REQ) (opcional, coincidencia parcial)",
        value=""
    )

    if st.button("🔄 Actualizar listado"):
        try:
            # Recargar datos frescos desde el CSV
            load_requerimientos_from_gsheet.clear()
            req_df = load_requerimientos_from_gsheet()

            if "ID_REQ" not in req_df.columns or "ESTATUS" not in req_df.columns:

                st.error(
                    "No pude encontrar columnas 'ID_REQ' y 'Estatus' en la hoja de requerimientos.\n\n"
                    f"Columnas leídas: {list(req_df.columns)}\n\n"
                    "Revisa que el CSV de requerimientos tenga esos encabezados en la fila 1."
                )
                st.stop()

            # Ordenar por Fecha/Hora si existen
            if "Fecha" in req_df.columns and "Hora" in req_df.columns:
                req_df_sorted = req_df.sort_values(
                    by=["Fecha", "Hora"], ascending=[True, True]
                )
            else:
                req_df_sorted = req_df.copy()

            # 🔹 Si hay folio escrito, filtramos TODO a ese folio
            if filtro_folio:
                mask = req_df_sorted["ID_REQ"].astype(str).str.lower() == filtro_folio.lower()
                df_filtrado = req_df_sorted[mask].copy()

                if df_filtrado.empty:
                    st.warning("No se encontró ningún requerimiento con ese ID_REQ.")
                    st.stop()
            else:
                df_filtrado = req_df_sorted

            # ---------- Resumen por ID_REQ (solo del filtrado) ----------
            agg_dict = {"ESTATUS": "last"}
            cols_resumen = ["ID_REQ", "ESTATUS"]

            if "FECHA DE PEDIDO" in df_filtrado.columns:
                agg_dict["FECHA DE PEDIDO"] = "last"
                cols_resumen.append("FECHA DE PEDIDO")
            if "FECHA DE RECEPCIÓN" in df_filtrado.columns:
                agg_dict["FECHA DE RECEPCIÓN"] = "last"
                cols_resumen.append("FECHA DE RECEPCIÓN")

            resumen = (
                df_filtrado
                .groupby("ID_REQ", as_index=False)
                .agg(agg_dict)
            )

            st.markdown("### 🗂 Resumen de requerimiento de compra ")
            st.dataframe(
                resumen[cols_resumen].reset_index(drop=True),
                use_container_width=True,
                hide_index=True
            )

            # ---------- Detalle SOLO si se buscó un folio ----------
            if filtro_folio:
                st.markdown(f"### 📄 Detalle de productos del folio: `{filtro_folio}`")

                detalle = df_filtrado.copy()

                cols_detalle = [c for c in [
                    "ID_REQ",
                    "INSUMO",
                    "UNIDAD DE MEDIDA",
                    "CANTIDAD",
                    "FECHA DE RECEPCIÓN" if "FECHA DE RECEPCIÓN" in detalle.columns else None,
                    "FACTURA",
                    "ESTATUS",
                    "OBSERVACIONES",
                ] if c is not None and c in detalle.columns]

                st.dataframe(
                    detalle[cols_detalle].reset_index(drop=True),
                    use_container_width=True,
                    hide_index=True
                )

        except Exception as e:
            st.error(
                "No se pudo cargar la hoja de requerimientos desde Google Sheets. "
                "Revisa REQUERIMIENTOS_CSV_URL en secrets y la publicación del archivo."
            )
            st.exception(e)
