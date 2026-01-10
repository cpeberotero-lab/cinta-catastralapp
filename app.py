import streamlit as st
import pandas as pd
import io

# Configuración de la página
st.set_page_config(page_title="Lector Cinta Catastral", layout="wide")

st.title("📂 Lector de Cinta Catastral (Formatos R1 y R2)")
st.markdown("""
**Instrucciones:**
1. Arrastre todos sus archivos **R1** y **R2** en la caja de abajo al mismo tiempo.
2. El sistema los clasificará y unificará automáticamente.
3. Use la pestaña de "Detalle Individual" para ver la ficha de un predio o descargue el Excel completo.
""")

# --- FUNCIONES DE PARSEO (Mantenemos tu lógica original) ---

def parse_r1(file_content):
    rows = []
    lines = file_content.decode('utf-8', errors='ignore').split('\n')
    
    for line in lines:
        if len(line) < 50: continue
        try:
            data = {
                'Codigo_Catastral_Completo': line[0:37].strip(),
                'Departamento_Municipio': line[0:5],
                'Sector_Manzana_Predio': line[5:30].strip(),
                'Nombre_Propietario': line[37:137].strip(),
                'Tipo_Documento': line[137:138].strip(),
                'Numero_Documento': line[138:153].strip(),
                'Direccion_Predio': line[153:253].strip(),
                'Destino_Economico': line[253:254].strip(),
                'Area_Terreno': line[254:266].strip(),
                'Area_Construida': line[266:278].strip(),
                'Avaluo': line[278:293].strip(),
                'Vigencia': line[293:297].strip() if len(line) > 297 else ''
            }
            # Conversiones numéricas
            try: data['Area_Terreno'] = float(data['Area_Terreno'])
            except: pass
            try: data['Area_Construida'] = float(data['Area_Construida'])
            except: pass
            try: data['Avaluo'] = float(data['Avaluo'])
            except: pass
            
            rows.append(data)
        except Exception:
            continue
    return pd.DataFrame(rows)

def parse_r2(file_content):
    rows = []
    lines = file_content.decode('utf-8', errors='ignore').split('\n')
    
    for line in lines:
        if len(line) < 50: continue
        try:
            data = {
                'Codigo_Catastral_Completo': line[0:37].strip(),
                'Codigo_Adicional': line[37:50].strip(),
                'Datos_Variables_R2': line[50:].strip()
            }
            rows.append(data)
        except:
            continue
    return pd.DataFrame(rows)

# --- INTERFAZ DE USUARIO: CARGA UNIFICADA ---

# Caja única para subir archivos
uploaded_files = st.file_uploader(
    "📥 Arrastre aquí sus archivos R1 y R2 (puede subir varios a la vez)", 
    type=['txt'], 
    accept_multiple_files=True
)

df_r1_list = []
df_r2_list = []

if uploaded_files:
    for uploaded_file in uploaded_files:
        # Detección automática basada en el nombre del archivo
        fname = uploaded_file.name.upper()
        
        if "R1" in fname:
            df = parse_r1(uploaded_file.getvalue())
            df_r1_list.append(df)
            st.toast(f"✅ R1 Detectado: {uploaded_file.name}", icon="📄")
            
        elif "R2" in fname:
            df = parse_r2(uploaded_file.getvalue())
            df_r2_list.append(df)
            st.toast(f"🏗️ R2 Detectado: {uploaded_file.name}", icon="📄")
        else:
            st.warning(f"⚠️ No se pudo identificar si '{uploaded_file.name}' es R1 o R2. Asegúrese que el nombre contenga 'R1' o 'R2'.")

    # Consolidar DataFrames si se subieron archivos
    df_main = pd.DataFrame()
    
    # Procesar R1
    if df_r1_list:
        df_r1_total = pd.concat(df_r1_list, ignore_index=True)
        # Procesar R2 (si existe)
        if df_r2_list:
            df_r2_total = pd.concat(df_r2_list, ignore_index=True)
            # Unir (Left Join)
            df_main = pd.merge(df_r1_total, df_r2_total, on='Codigo_Catastral_Completo', how='left', suffixes=('_R1', '_R2'))
        else:
            df_main = df_r1_total
            st.info("ℹ️ Solo se cargó información R1. Los datos de construcción (R2) no estarán disponibles.")
    
    if not df_main.empty:
        st.success("✅ Procesamiento completado exitosamente")

        # --- PESTAÑAS DE NAVEGACIÓN ---
        tab1, tab2, tab3 = st.tabs(["🔍 Detalle Individual", "📊 Tablas de Datos", "📥 Descargas"])

        # --- PESTAÑA 1: VISOR DETALLADO ---
        with tab1:
            st.subheader("Ficha del Predio")
            
            # Crear una columna combinada para el buscador
            df_main['Busqueda_Label'] = df_main['Codigo_Catastral_Completo'] + " | " + df_main['Nombre_Propietario']
            
            # Selector inteligente
            seleccion = st.selectbox(
                "Busque y seleccione un predio (Escriba nombre o código):", 
                df_main['Busqueda_Label'].unique()
            )
            
            if seleccion:
                # Filtrar el dato seleccionado
                dato = df_main[df_main['Busqueda_Label'] == seleccion].iloc[0]
                
                # Diseño de tarjeta con columnas
                c1, c2 = st.columns([1, 2])
                
                with c1:
                    st.info("👤 **Información del Titular**")
                    st.write(f"**Nombre:** {dato['Nombre_Propietario']}")
                    st.write(f"**Documento:** {dato['Numero_Documento']} ({dato['Tipo_Documento']})")
                    
                    st.divider()
                    st.success("💰 **Información Económica**")
                    val_avaluo = dato['Avaluo'] if pd.notnull(dato['Avaluo']) else 0
                    st.metric("Avalúo Catastral", f"${val_avaluo:,.0f}")
                    st.write(f"**Destino:** {dato['Destino_Economico']}")
                    st.write(f"**Vigencia:** {dato['Vigencia']}")

                with c2:
                    st.warning("🏠 **Información del Predio**")
                    st.write(f"**Código Catastral:** `{dato['Codigo_Catastral_Completo']}`")
                    st.write(f"**Dirección:** {dato['Direccion_Predio']}")
                    st.write(f"**Municipio:** {dato['Departamento_Municipio']}")
                    
                    cc1, cc2 = st.columns(2)
                    cc1.metric("Área Terreno", f"{dato['Area_Terreno']:,.2f} m²")
                    cc2.metric("Área Construida", f"{dato['Area_Construida']:,.2f} m²")
                    
                    if 'Datos_Variables_R2' in dato and pd.notnull(dato['Datos_Variables_R2']):
                        with st.expander("Ver Datos Crudos de Construcción (R2)"):
                            st.text(dato['Datos_Variables_R2'])
                    elif df_r2_list:
                        st.caption("Sin datos R2 asociados a este predio específico.")

        # --- PESTAÑA 2: TABLA GENERAL ---
        with tab2:
            st.subheader("Base de Datos Completa")
            st.dataframe(df_main)
            st.caption(f"Total de registros cargados: {len(df_main)}")

        # --- PESTAÑA 3: DESCARGAS ---
        with tab3:
            st.header("Exportar Datos")
            
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_main.drop(columns=['Busqueda_Label'], errors='ignore').to_excel(writer, sheet_name='Consolidado', index=False)
                if df_r1_list:
                    df_r1_total.to_excel(writer, sheet_name='R1_Original', index=False)
                if df_r2_list:
                    df_r2_total.to_excel(writer, sheet_name='R2_Original', index=False)
            
            st.download_button(
                label="📥 Descargar Excel Consolidado",
                data=buffer.getvalue(),
                file_name="Reporte_Catastral_Final.xlsx",
                mime="application/vnd.ms-excel"
            )

else:
    st.info("Esperando archivos... Por favor cargue los archivos .TXT en la parte superior.")
