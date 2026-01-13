import streamlit as st
import pandas as pd
import io

# Configuración de la página
st.set_page_config(page_title="Lector Cinta Catastral", layout="wide")

# --- ESTILOS CSS PERSONALIZADOS ---
st.markdown("""
    <style>
    /* Estilo para el Footer */
    .footer {
        margin-top: 50px;
        margin-bottom: 30px;
        text-align: center;
        color: #94a3b8; /* Slate 400 */
        font-family: sans-serif;
        font-size: 12px; /* text-xs */
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    .footer-bold {
        font-weight: bold;
        margin: 0;
    }
    .footer-link {
        color: #3b82f6; /* Blue 500 */
        text-decoration: none;
        transition: all 0.3s ease;
    }
    .footer-link:hover {
        color: #1d4ed8; /* Blue 700 */
        text-decoration: underline;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📂 Lector de Cinta Catastral (Formatos R1 y R2)")
st.markdown("""
**Instrucciones:**
1. Arrastre todos sus archivos **R1** y **R2** en la caja de carga.
2. El sistema generará automáticamente la **Referencia Catastral (20 dígitos)** para facilitar la búsqueda.
""")

# --- FUNCIONES DE PARSEO OPTIMIZADAS ---

def parse_r1(file_content):
    """
    Parsea R1 y genera la Referencia Catastral de 20 dígitos.
    Estructura analizada:
    - 0-5: Dept/Mun (08141)
    - 5-9: Sector/Corregimiento (4 dígitos)
    - 10-21: Manzana/Predio (11 dígitos finales del bloque)
    Total: 20 dígitos.
    """
    rows = []
    lines = file_content.decode('utf-8', errors='ignore').split('\n')
    
    for line in lines:
        if len(line) < 50: continue
        try:
            # Extracción de datos básicos
            cod_completo_archivo = line[0:37].strip() # Código largo original
            
            # --- GENERACIÓN CÓDIGO 20 DÍGITOS ---
            # Bloque 1: 08141 (5 chars)
            part1 = line[0:5] 
            # Bloque 2: Sector/Corregimiento (4 chars)
            part2 = line[5:9] 
            # Bloque 3: Manzana/Predio (11 chars) - Se toma desde el 10 para omitir padding
            part3 = line[10:21]
            
            ref_catastral_20 = f"{part1}{part2}{part3}"

            # Resto de campos
            nombre = line[37:137].strip() 
            tipo_doc = line[138:139].strip()
            num_doc = line[139:151].strip()
            direccion = line[151:251].strip()
            destino = line[252:253].strip()
            
            s_area_t = line[253:268].strip()
            s_area_c = line[268:279].strip()
            s_avaluo = line[279:289].strip()
            s_vigencia = line[293:297].strip()

            # Conversiones numéricas
            area_t = 0.0
            area_c = 0.0
            avaluo = 0.0
            
            if s_area_t: 
                try: area_t = float(s_area_t)
                except: pass
            if s_area_c:
                try: 
                    raw_ac = float(s_area_c)
                    area_c = raw_ac / 100000.0 if raw_ac > 0 else 0
                except: pass
            if s_avaluo:
                try: avaluo = float(s_avaluo)
                except: pass

            data = {
                'Referencia_Catastral': ref_catastral_20, # NUEVO CAMPO PRINCIPAL
                'Codigo_Archivo_Original': cod_completo_archivo,
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
                'Codigo_Archivo_Original': line[0:37].strip(), # Usamos este para el cruce (Join)
                'Codigo_Adicional': line[37:50].strip(),
                'Datos_Variables_R2': line[50:].strip()
            }
            rows.append(data)
        except:
            continue
    return pd.DataFrame(rows)

# --- INTERFAZ DE USUARIO ---

uploaded_files = st.file_uploader(
    "📥 Carga Unificada (Archivos R1 y R2)", 
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
            
        elif "R2" in fname:
            df = parse_r2(uploaded_file.getvalue())
            df_r2_list.append(df)

    # Consolidación
    df_main = pd.DataFrame()
    
    if df_r1_list:
        df_r1_total = pd.concat(df_r1_list, ignore_index=True)
        if df_r2_list:
            df_r2_total = pd.concat(df_r2_list, ignore_index=True)
            # El cruce se hace por el código largo original del archivo para asegurar integridad
            df_main = pd.merge(df_r1_total, df_r2_total, on='Codigo_Archivo_Original', how='left', suffixes=('', '_R2'))
        else:
            df_main = df_r1_total
            st.warning("Solo se cargaron archivos R1 (Básicos).")
    
    if not df_main.empty:
        st.success(f"✅ Se cargaron {len(df_main)} registros correctamente.")

        # --- ESTRUCTURA DE PESTAÑAS ---
        tab_owner, tab_detail, tab_data, tab_export = st.tabs([
            "👤 Portafolio Propietario", 
            "🏠 Ficha Predial (Búsqueda)", 
            "📊 Tabla General", 
            "📥 Exportar"
        ])

        # --- PESTAÑA 1: PORTAFOLIO POR PROPIETARIO ---
        with tab_owner:
            st.header("Resumen por Contribuyente")
            
            lista_propietarios = sorted(df_main['Nombre_Propietario'].dropna().unique())
            
            seleccion_prop = st.selectbox(
                "Seleccione Propietario:", 
                lista_propietarios,
                index=None,
                placeholder="Escriba para buscar..."
            )

            if seleccion_prop:
                portfolio = df_main[df_main['Nombre_Propietario'] == seleccion_prop]
                
                total_predios = len(portfolio)
                suma_avaluos = portfolio['Avaluo'].sum()
                suma_area_t = portfolio['Area_Terreno'].sum()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Predios", total_predios, border=True)
                c2.metric("Patrimonio (Avalúo Total)", f"${suma_avaluos:,.0f}", border=True)
                c3.metric("Área Total Terreno", f"{suma_area_t:,.0f} m²", border=True)
                
                st.subheader(f"Detalle de Propiedades de: {seleccion_prop}")
                
                display_cols = ['Referencia_Catastral', 'Direccion_Predio', 'Destino_Economico', 'Avaluo', 'Area_Terreno']
                st.dataframe(
                    portfolio[display_cols].style.format({
                        'Avaluo': '${:,.0f}', 
                        'Area_Terreno': '{:,.0f}'
                    }),
                    use_container_width=True
                )

        # --- PESTAÑA 2: FICHA TÉCNICA (INDIVIDUAL) ---
        with tab_detail:
            st.subheader("Búsqueda por Referencia Catastral (20 Dígitos)")
            
            # Creamos la columna de búsqueda combinando la REF 20 DIGITOS + NOMBRE
            df_main['Busqueda'] = df_main['Referencia_Catastral'] + " | " + df_main['Nombre_Propietario']
            
            seleccion = st.selectbox(
                "Busque por Referencia (Ej: 08141...) o Nombre:", 
                df_main['Busqueda'].unique(),
                placeholder="Escriba el código catastral de 20 dígitos..."
            )
            
            if seleccion:
                row = df_main[df_main['Busqueda'] == seleccion].iloc[0]
                
                col_a, col_b = st.columns([1, 2])
                with col_a:
                    st.info(f"**Propietario:** {row['Nombre_Propietario']}")
                    st.write(f"**CC/NIT:** {row['Numero_Documento']}")
                    st.divider()
                    st.metric("Avalúo 2024", f"${row['Avaluo']:,.0f}")
                
                with col_b:
                    st.warning(f"**Dirección:** {row['Direccion_Predio']}")
                    # Mostramos la Referencia Catastral Limpia (20 dígitos)
                    st.markdown("### Referencia Catastral")
                    st.code(row['Referencia_Catastral'], language="text")
                    
                    c_x, c_y = st.columns(2)
                    c_x.metric("Terreno", f"{row['Area_Terreno']:,.0f} m²")
                    c_y.metric("Construido", f"{row['Area_Construida']:,.2f} m²")

        # --- PESTAÑA 3: TABLA COMPLETA ---
        with tab_data:
            # Reordenamos columnas para que la Ref 20 sea la primera
            cols = ['Referencia_Catastral', 'Nombre_Propietario', 'Avaluo', 'Direccion_Predio', 'Area_Terreno', 'Area_Construida']
            st.dataframe(df_main[cols])

        # --- PESTAÑA 4: EXPORTAR ---
        with tab_export:
            st.write("Descargue la información procesada en Excel.")
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                # Exportamos la tabla limpia
                df_main.drop(columns=['Busqueda'], errors='ignore').to_excel(writer, sheet_name='Consolidado', index=False)
                
            st.download_button(
                label="📥 Descargar Excel",
                data=buffer.getvalue(),
                file_name="Reporte_Catastral_2024.xlsx",
                mime="application/vnd.ms-excel"
            )

else:
    st.info("👋 Bienvenido. Cargue sus archivos TXT para comenzar.")

# --- FOOTER ---
st.markdown("""
    <div class="footer">
        <p class="footer-bold">Simple Taxes S.A.S. &copy; 2025</p>
        <a href="https://simpletaxes.com.co/politica-de-privacidad-y-tratamiento-de-datos/" target="_blank" class="footer-link">
            Política de Privacidad y Tratamiento de Datos
        </a>
    </div>
""", unsafe_allow_html=True)
