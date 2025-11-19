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
    "6) Consolida los movimientos en un Google Sheets central mediante Apps Script."
)

# --------------------------------------------------
# Columnas que el USUARIO debe llenar en Movimientos_Inventario
# (NO incluimos ID ni Timestamp porque se generan en el código)
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
# Inicializar session_state para último inventario
# --------------------------------------------------
if "ultimo_inventario_df" not in st.session_state:
    st.session_state["ultimo_inventario_df"] = None
if "ultimo_inventario_folio" not in st.session_state:
    st.session_state["ultimo_inventario_folio"] = None
if "ultimo_inventario_fecha" not in st.session_state:
    st.session_state["ultimo_inventario_fecha"] = None
if "ultimo_inventario_hora" not in st.session_state:
    st.session_state["ultimo_inventario_hora"] = None


# --------------------------------------------------
# Funciones auxiliares
# --------------------------------------------------

@st.cache_data
def load_movimientos_template_from_gsheet() -> pd.DataFrame:
    """
    Carga la hoja Movimientos_Inventario desde Google Sheets (CSV publicado).
    SOLO LECTURA: no modifica el Sheet.
    Solo necesitamos los encabezados, así que leemos solo la fila de columnas.
    """
    sheet_url = st.secrets["MOVIMIENTOS_TEMPLATE_CSV_URL"]

    try:
        # Leemos solo headers (nrows=0 evita problemas con filas sucias abajo)
        df = pd.read_csv(sheet_url, nrows=0)
    except pd.errors.ParserError:
        # Plan B: leer con engine='python' y saltar líneas malas
        df_full = pd.read_csv(
            sheet_url,
            engine="python",
            on_bad_lines="skip"
        )
        df = df_full.iloc[0:0].copy()

    df.columns = df.columns.str.strip()
    return df


def df_to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Movimientos") -> BytesIO:
    """
    Convierte un DataFrame a un archivo Excel en memoria (BytesIO)
    para poder usarlo en st.download_button.
    """
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output


def detectar_extension(nombre_archivo: str) -> str:
    """
    Devuelve la extensión del archivo en minúsculas, sin el punto.
    """
    return os.path.splitext(nombre_archivo)[1].lower().replace(".", "")


def leer_archivo_movimientos(uploaded_file) -> pd.DataFrame:
    """
    Lee el archivo de movimientos que sube el usuario.
    Cubre:
      - XLSX / XLS: intenta hoja 'Movimientos_Inventario', si no existe toma la primera.
      - CSV: lo lee como CSV estándar.
    Normaliza headers (strip).
    """
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
    """
    Valida que el DataFrame tenga al menos las columnas que el usuario debe llenar (USER_COLUMNS).
    Ignora columnas extra.
    Reordena el DF para que queden en el orden de USER_COLUMNS.
    """
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
    """
    Genera folio de inventario + fecha y hora locales (CDMX).
    Formato folio: INV-YYYYMMDD-HHMMSS
    """
    tz = pytz.timezone("America/Mexico_City")
    ahora = datetime.now(tz)
    folio = ahora.strftime("INV-%Y%m%d-%H%M%S")
    fecha = ahora.date().isoformat()
    hora = ahora.strftime("%H:%M:%S")
    return folio, fecha, hora


def agregar_campos_sistema(df: pd.DataFrame, folio: str, fecha: str, hora: str) -> pd.DataFrame:
    """
    Agrega columnas generadas por el sistema:
      - ID: folio único por archivo subido (mismo valor para todas las filas)
      - Fecha_Carga
      - Hora_Carga
    """
    df = df.copy()

    # ID = folio único de la carga (igual para todas las filas)
    df["ID"] = folio

    # Fecha y hora de carga
    df["Fecha_Carga"] = fecha
    df["Hora_Carga"] = hora

    # Reordenar: primero ID, luego las columnas del usuario, luego campos de sistema
    ordered_cols = (
        ["ID"] +
        [c for c in USER_COLUMNS if c in df.columns] +
        [c for c in ["Fecha_Carga", "Hora_Carga"] if c in df.columns]
    )
    df = df[ordered_cols]

    return df


def enviar_a_consolidado(df: pd.DataFrame):
    """
    Envía el DF procesado al Google Sheets de consolidado usando Apps Script.
    - Convierte objetos Timestamp/datetime/date a strings ISO.
    - Reemplaza NaN/NaT por None para que sean JSON-serializable.
    """
    url = st.secrets.get("APPS_SCRIPT_CONSOLIDADO_URL", "")

    if not url:
        st.warning(
            "No se configuró APPS_SCRIPT_CONSOLIDADO_URL en secrets. "
            "No se enviará nada al consolidado."
        )
        return

    df_json = df.copy()

    # Helper para convertir tipos no JSON-serializables
    def to_jsonable(x):
        if isinstance(x, (pd.Timestamp, datetime, date)):
            return x.isoformat()
        return x

    # Aplicar conversión a toda la tabla
    df_json = df_json.applymap(to_jsonable)

    # Asegurar que NaN/NaT se vuelvan None
    df_json = df_json.astype(object).where(pd.notnull(df_json), None)

    # Convertir a lista de listas
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
# Selector de vista
# --------------------------------------------------
vista = st.sidebar.radio(
    "Selecciona vista:",
    ("📥 Carga de inventario", "📊 Último inventario cargado")
)

# --------------------------------------------------
# VISTA 1: Carga de inventario
# --------------------------------------------------
if vista == "📥 Carga de inventario":
    st.header("📥 Carga de inventario")

    # 1. Estructura base desde Google Sheets (solo para ver headers)
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

    # 2. Descargar plantilla de inventario (directo desde Google Sheets, con fórmulas y productos)
    st.subheader("2. Descargar plantilla de inventario")

    st.write(
        "Descarga la plantilla oficial desde Google Sheets. "
        "Incluye la hoja **Movimientos_Inventario** (para captura) y la hoja **Productos** "
        "con sus fórmulas. No modifiques los nombres de las hojas."
    )

    # URL de export a XLSX de tu sheet publicado (plantilla con 2 hojas)
    url_plantilla_xlsx = (
        "https://docs.google.com/spreadsheets/d/e/"
        "2PACX-1vQ4Q30Ldblb-_bxRPugOXBCGU97CrsHozkf0conSHypwdVruRtH9UNXeT2D9mdu8XfDLknMk1UH2UBs/"
        "pub?output=xlsx"
    )

    st.markdown(
        f"[⬇️ Descargar plantilla de inventario (Excel con productos y fórmulas)]({url_plantilla_xlsx})",
        unsafe_allow_html=True
    )

    # 3. Subir archivo lleno y procesar
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

            # Validar columnas y ordenarlas (solo las del usuario)
            mov_df = validar_y_ordenar_columnas(mov_df)

            # Filtrar filas donde la columna 'Cantidad' sea > 0
            cantidades = pd.to_numeric(mov_df["Cantidad"], errors="coerce").fillna(0)
            filtrado_df = mov_df[cantidades > 0].copy()

            st.write(f"Filas con **Cantidad > 0**: **{len(filtrado_df)}**")

            if len(filtrado_df) > 0:
                # Generar folio + fecha/hora
                folio, fecha, hora = generar_folio_inventario()

                # Agregar columnas de sistema (ID=folio, Fecha_Carga, Hora_Carga)
                filtrado_df = agregar_campos_sistema(filtrado_df, folio, fecha, hora)

                st.markdown("### Movimientos filtrados (solo con Cantidad > 0)")
                st.dataframe(filtrado_df, use_container_width=True)

                st.info(
                    f"Folio de inventario generado (ID de la carga): **{folio}**\n\n"
                    f"Fecha de carga: **{fecha}**  \n"
                    f"Hora de carga: **{hora}**"
                )

                # Guardar en session_state
                st.session_state["ultimo_inventario_df"] = filtrado_df
                st.session_state["ultimo_inventario_folio"] = folio
                st.session_state["ultimo_inventario_fecha"] = fecha
                st.session_state["ultimo_inventario_hora"] = hora

                # Enviar al consolidado en Google Sheets B
                enviar_a_consolidado(filtrado_df)

                # Descargar resultado
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
