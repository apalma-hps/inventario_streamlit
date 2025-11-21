import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime, date
import pytz
import os
import requests

# --------------------------------------------------
# Configuración básica de la página
# --------------------------------------------------
st.set_page_config(
    page_title="Inventario – Movimientos",
    page_icon="📦",
    layout="wide"
)

st.title("📦 Sistema de Movimientos de Inventario")

st.write(
    "Flujo:\n"
    "1) Descargan la plantilla oficial desde Google Sheets (incluye hoja de productos).\n"
    "2) Llenan la hoja **Movimientos_Inventario** en Excel/CSV.\n"
    "3) Suben el archivo.\n"
    "4) El sistema filtra solo lo que tiene cantidad.\n"
    "5) Genera un **folio único** por carga (columna `ID`) y agrega fecha/hora.\n"
    "6) Consolida los movimientos en un Google Sheets central mediante Apps Script.\n"
    "7) Permite generar y consultar requerimientos de producto."
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
]

# --------------------------------------------------
# Columnas en la hoja de Requerimientos (consolidado)
# --------------------------------------------------
REQUERIMIENTOS_COLUMNS = [
    "FECHA DE PEDIDO",
    "PROVEDOR",
    "INSUMO",
    "UNIDAD DE MEDIDA",
    "CANTIDAD",
    "COSTO UNIDAD",
    "COSTO TOTAL",
    "FECHA DE ENTREGA",
    "Factura",
    "Observaciones",
    "Estatus",
    "ID_REQ",
    "Fecha",
    "Hora",
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
    """
    Carga la hoja 'Catalogo_Productos' desde la plantilla.
    Solo usa la columna 'Producto' y elimina filas vacías / NaN.
    """
    df = pd.read_excel(
        PLANTILLA_INVENTARIO_XLSX_URL,
        sheet_name="Catalogo_Productos"
    )

    df.columns = df.columns.astype(str).str.strip()

    if "Producto" not in df.columns:
        raise ValueError("La hoja Catalogo_Productos no contiene la columna 'Producto'.")

    # Solo columna Producto
    df = df[["Producto"]].copy()

    # 1) Quitar NaN reales
    df = df[df["Producto"].notna()]

    # 2) Normalizar texto (AQUÍ estaba el error: ahora usamos .str.strip())
    df["Producto"] = df["Producto"].astype(str).str.strip()

    # 3) Quitar strings vacíos o "nan" como texto
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
            rename_map[col] = "Estatus"
        elif n == "fechadepedido":
            rename_map[col] = "FECHA DE PEDIDO"
        elif n == "fechadeentrega":
            rename_map[col] = "FECHA DE ENTREGA"

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
    "Selecciona vista:",
    (
        "📥 Carga de inventario",
        "📊 Último inventario cargado",
        "📨 Requerimientos de producto",
    )
)

# --------------------------------------------------
# VISTA 1: Carga de inventario
# --------------------------------------------------
if vista == "📥 Carga de inventario":
    st.header("📥 Carga de inventario")

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
        "Descarga la plantilla oficial desde Google Sheets. "
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
elif vista == "📊 Último inventario cargado":
    st.header("📊 Último inventario cargado en esta sesión")

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
            "Catálogo de productos cargado desde la plantilla de inventario "
            "(hoja Catalogo_Productos)."
        )

        with st.expander("Ver catálogo completo de productos"):
            st.dataframe(productos_df, use_container_width=True)

    except Exception as e:
        st.error(
            "No se pudo cargar el catálogo de productos desde la plantilla de inventario. "
            "Revisa que exista la hoja 'Catalogo_Productos'."
        )
        st.exception(e)
        st.stop()

    productos_unicos = sorted(
        productos_df["Producto"].dropna().astype(str).unique().tolist()
    )
    OPCION_OTRO = "Otro producto (no está en el catálogo)"
    opciones_productos = ["--- Selecciona un producto ---"] + productos_unicos + [OPCION_OTRO]

    # ---------- 2) Formulario de captura (cabecera + línea de producto) ----------
    st.subheader("📝 Crear nuevo requerimiento (carrito de productos)")

    with st.form("form_requerimiento"):
        col1, col2 = st.columns(2)

        usuario = col1.text_input("Usuario solicitante")
        ceco_destino = col1.text_input("CECO destino")
        proveedor = col1.text_input("Proveedor")

        fecha_requerida = col2.date_input(
            "Fecha requerida (fecha de entrega)",
            value=date.today()
        )
        prioridad = col2.selectbox(
            "Prioridad",
            options=["Media", "Alta", "Baja"],
            index=0
        )

        st.markdown("### Producto a agregar al requerimiento")

        producto_sel = st.selectbox("Producto", opciones_productos)

        es_nuevo = False
        producto_final = None

        if producto_sel == OPCION_OTRO:
            es_nuevo = True
            st.info("Captura datos para agregar un nuevo producto al catálogo.")
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

        factura = st.text_input("Factura (si aplica, para este producto)")
        observaciones = st.text_area("Observaciones (para este producto)")

        colb1, colb2 = st.columns(2)
        add_line = colb1.form_submit_button("➕ Agregar producto al requerimiento")
        send_req = colb2.form_submit_button("✅ Confirmar y enviar requerimiento")

    # ---------- 2.a) Manejar botón: Agregar producto al carrito ----------
    if add_line:
        errores = []
        if producto_final is None or producto_final == "":
            errores.append("Debes seleccionar un producto o capturar uno nuevo.")
        if cantidad <= 0:
            errores.append("La *Cantidad requerida* debe ser mayor a 0.")

        if errores:
            st.error("No se pudo agregar el producto al requerimiento:")
            for e in errores:
                st.write("-", e)
        else:
            # si es nuevo y tiene nombre, mandamos al catálogo (opcional)
            if es_nuevo and producto_final:
                enviar_nuevo_producto_a_catalogo(producto_final)

            item = {
                "INSUMO": producto_final,
                "UNIDAD DE MEDIDA": "pz",
                "CANTIDAD": cantidad,
                "Factura": factura,
                "Observaciones": observaciones,
            }
            st.session_state["carrito_req"].append(item)
            st.success(f"Producto agregado al requerimiento: {producto_final} (Cantidad: {cantidad})")

    # ---------- Vista del carrito actual ----------
    if st.session_state["carrito_req"]:
        st.markdown("### 🛒 Carrito de productos del requerimiento actual")
        carrito_df = pd.DataFrame(st.session_state["carrito_req"])
        st.dataframe(carrito_df, use_container_width=True)

        if st.button("🗑️ Vaciar carrito"):
            st.session_state["carrito_req"] = []
            st.info("Carrito vaciado.")

    # ---------- 2.b) Manejar botón: Confirmar y enviar requerimiento ----------
    if send_req:
        errores = []
        if not usuario:
            errores.append("Debes capturar el *Usuario solicitante*.")
        if not ceco_destino:
            errores.append("Debes capturar el *CECO destino*.")
        if not proveedor:
            errores.append("Debes capturar el *Proveedor*.")
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
                    "PROVEDOR": proveedor,
                    "INSUMO": item["INSUMO"],
                    "UNIDAD DE MEDIDA": item["UNIDAD DE MEDIDA"],
                    "CANTIDAD": item["CANTIDAD"],
                    "COSTO UNIDAD": "",
                    "COSTO TOTAL": "",
                    "FECHA DE ENTREGA": fecha_requerida.isoformat(),
                    "Factura": item["Factura"],
                    "Observaciones": item["Observaciones"],
                    "Estatus": "Pendiente",
                    "ID_REQ": folio_req,
                    "Fecha": fecha_creacion,
                    "Hora": hora_creacion,
                }
                lista_req_data.append(req_data)

            enviar_requerimientos_a_gsheet(lista_req_data)
            # si todo va bien, vaciamos el carrito
            st.session_state["carrito_req"] = []

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

            if "ID_REQ" not in req_df.columns or "Estatus" not in req_df.columns:
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
            agg_dict = {"Estatus": "last"}
            cols_resumen = ["ID_REQ", "Estatus"]

            if "FECHA DE PEDIDO" in df_filtrado.columns:
                agg_dict["FECHA DE PEDIDO"] = "last"
                cols_resumen.append("FECHA DE PEDIDO")
            if "FECHA DE ENTREGA" in df_filtrado.columns:
                agg_dict["FECHA DE ENTREGA"] = "last"
                cols_resumen.append("FECHA DE ENTREGA")

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
                    "FECHA DE ENTREGA" if "FECHA DE ENTREGA" in detalle.columns else None,
                    "Factura",
                    "Estatus",
                    "Observaciones",
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
