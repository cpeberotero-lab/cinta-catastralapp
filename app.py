import streamlit as st
import pandas as pd
import io

# Configuración de la página
st.set_page_config(page_title="Lector Cinta Catastral", layout="wide")

st.title("📂 Lector de Cinta Catastral (Formatos R1 y R2)")
st.markdown("""
**Instrucciones:**
1. Arrastre todos sus archivos **R1** y **R2** en la caja de abajo al mismo tiempo.
2. El sistema unificará la información y corregirá automáticamente los valores de avalúo y áreas.
""")

# --- FUNCIONES DE PARSEO CORREGIDAS (Precisión IGAC) ---

def parse_r1(file_content):
    """
    Parsea el archivo R1 con índices ajustados tras auditoría con Excel 2024.
    Estructura detectada:
    - Destino: Pos 252 (1 char)
    - Area Terreno: Pos 253 (15 chars) -> Entero
    - Area Construida: Pos 268 (11 chars) -> Con 5 decimales implícitos
    - Avaluo: Pos 279 (10 chars) -> Entero
    - Fecha/Vigencia: Pos 289
    """
    rows = []
    lines = file_content.decode('utf-8', errors='ignore').split('\n')
    
    for line in lines:
        if len(line) < 50: continue
        try:
            # Índices ajustados al estándar detectado en "Fondo Ganadero"
            # Nota: Python usa índice base 0.
            
            # --- Bloque Identificación ---
            cod_catastral = line[0:37].strip()
            # El nombre va hasta el 137, pero a veces muerde el tipo doc si es muy largo, ajustamos
            nombre = line[37:137].strip() 
            
            # --- Bloque Documento (Ajustado) ---
            tipo_doc = line[138:139].strip() # Posición 138 exacta
            num_doc = line[139:151].strip()  # 12 dígitos siguientes
            
            # --- Bloque Ubicación ---
            direccion = line[151:251].strip() # 100 caracteres de dirección
            
            # --- Bloque Económico (El más crítico) ---
            destino = line[252:253].strip()
            
            # Extracción de cadenas numéricas
            s_area_t = line[253:268].strip() # 15 chars
            s_area_c = line[268:279].strip() # 11 chars
            s_avaluo = line[279:289].strip() # 10 chars
            s_vigencia = line[293:297].strip() # Tomamos solo el año (2024) de la fecha completa
            
            # Conversión numérica segura
            area_t = 0.0
            area_c = 0.0
            avaluo = 0.0
            
            if s_area_t: 
                try: area_t = float(s_area_t)
                except: pass
                
            if s_area_c:
                try: 
                    # El área construida suele venir como 0011200000 (112 m2). Dividimos por 100,000
                    raw_ac = float(s_area_c)
                    area_c = raw_ac / 100000.0 if raw_ac > 0 else 0
                except: pass
                
            if s_avaluo:
                try: avaluo = float(s_avaluo)
                except: pass

            data = {
                'Codigo_Catastral_Completo': cod_catastral,
                'Departamento_Municipio': line[0:5],
                'Nombre_Propietario': nombre,
                'Tipo_Documento': tipo_doc,
                'Numero_Documento': num_doc,
                'Direccion_Predio': direccion,
                'Destino_Economico': destino,
                'Area_Terreno': area_t,
                'Area_Construida': area_c,
                'Avaluo': avaluo,
                'Vigencia': s_vigencia
            }
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

# --- INTERFAZ DE USUARIO ---

uploaded_files = st.file_uploader(
    "📥 Arrastre aquí sus archivos R1 y R2 (Carga Unificada)", 
    type=['txt'], 
    accept_multiple_files=True
)

df_r1_list = []
df_r2_list = []

if uploaded_files:
    for uploaded_file in uploaded_files:
        fname = uploaded_file.name.upper()
        
        if "R1" in fname:
            df = parse_r1(uploaded_file.getvalue())
            df_r1_list.append(df)
            st.toast(f"✅ R1 Procesado: {uploaded_file.name}", icon="📄")
            
        elif "R2" in fname:
            df = parse_r2(uploaded_file.getvalue())
            df_r2_list.append(df)
            st.toast(f"🏗️ R2 Procesado: {uploaded_file.name}", icon="📄")

    # Consolidación
    df_main = pd.DataFrame()
    
    if df_r1_list:
        df_r1_total = pd.concat(df_r1_list, ignore_index=True)
        
        if df_r2_list:
            df_r2_total = pd.concat(df_r2_list, ignore_index=True)
            df_main = pd.merge(df_r1_total, df_r2_total, on='Codigo_Catastral_Completo', how='left', suffixes=('', '_R2'))
        else:
            df_main = df_r1_total
            st.info("ℹ️ Solo se detectó información R1.")
    
    if not df_main.empty:
        st.success("✅ Datos cargados y corregidos exitosamente")

        # --- PESTAÑAS ---
        tab1, tab2, tab3 = st.tabs(["🔍 Ficha Técnica", "📊 Tabla General", "📥 Exportar"])

        # PESTAÑA 1: BÚSQUEDA DETALLADA
        with tab1:
            st.subheader("Consulta Individual de Predios")
            
            # Columna auxiliar para buscador
            df_main['Busqueda'] = df_main['Codigo_Catastral_Completo'] + " | " + df_main['Nombre_Propietario']
            
            seleccion = st.selectbox(
                "Busque por Nombre o Código Catastral:", 
                df_main['Busqueda'].unique()
            )
            
            if seleccion:
                row = df_main[df_main['Busqueda'] == seleccion].iloc[0]
                
                # Diseño de Tarjeta
                c1, c2 = st.columns([1, 1.5])
                
                with c1:
                    st.markdown("### 👤 Propietario")
                    st.info(f"**{row['Nombre_Propietario']}**")
                    st.write(f"**Doc:** {row['Tipo_Documento']} {row['Numero_Documento']}")
                    
                    st.markdown("### 💰 Avalúo Catastral")
                    # Formato moneda sin decimales
                    st.metric("Valor", f"${row['Avaluo']:,.0f}")
                    st.caption(f"Vigencia: {row['Vigencia']}")

                with c2:
                    st.markdown("### 🏠 Datos del Predio")
                    st.write(f"**Dirección:** {row['Direccion_Predio']}")
                    st.code(row['Codigo_Catastral_Completo'], language="text")
                    
                    mc1, mc2 = st.columns(2)
                    mc1.metric("Área Terreno", f"{row['Area_Terreno']:,.0f} m²")
                    mc2.metric("Área Construida", f"{row['Area_Construida']:,.2f} m²")
                    
                    st.markdown(f"**Destino Económico:** {row['Destino_Economico']}")

        # PESTAÑA 2: TABLA
        with tab2:
            st.dataframe(df_main)

        # PESTAÑA 3: DESCARGA
        with tab3:
            st.header("Descargar Reporte")
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                # Hoja Principal
                df_export = df_main.drop(columns=['Busqueda'], errors='ignore')
                df_export.to_excel(writer, sheet_name='Consolidado', index=False)
                
                # Ajustar ancho de columnas en Excel para que se vea bonito
                worksheet = writer.sheets['Consolidado']
                worksheet.set_column('A:A', 30) # Codigo
                worksheet.set_column('C:C', 40) # Nombre
                worksheet.set_column('F:F', 40) # Direccion
                worksheet.set_column('J:J', 15) # Avaluo
                
            st.download_button(
                label="📥 Descargar Excel Corregido",
                data=buffer.getvalue(),
                file_name="Reporte_Catastral_2024.xlsx",
                mime="application/vnd.ms-excel"
            )

else:
    st.info("Esperando archivos... Por favor suba sus .TXT")
