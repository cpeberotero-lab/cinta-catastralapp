import streamlit as st
import pandas as pd
import io

# Configuración de la página
st.set_page_config(page_title="Lector Cinta Catastral", layout="wide")

st.title("📂 Lector de Cinta Catastral")
st.markdown("""
Esta aplicación permite cargar, procesar y visualizar archivos de cinta catastral (IGAC).
Cargue sus archivos **** (Información Básica) y **** (Información Económica/Construcción) para comenzar.
""")

# --- FUNCIONES DE PARSEO ---

def parse_r1(file_content):
    """
    Parsea el archivo R1 (Registro 1 - Datos del Propietario y Predio).
    Basado en estructura fija deducida de archivos IGAC.
    """
    rows = []
    lines = file_content.decode('utf-8', errors='ignore').split('\n')
    
    for line in lines:
        if len(line) < 50: continue # Saltar líneas vacías
        
        try:
            # Definición de cortes (slices) basada en el estándar visual del archivo adjunto
            # Ajustar estos índices si la estructura varía levemente
            data = {
                'Codigo_Catastral_Completo': line[0:37].strip(),
                'Departamento_Municipio': line[0:5],
                'Sector_Manzana_Predio': line[5:30].strip(), # Parte central del predial
                'Nombre_Propietario': line[37:137].strip(),  # Aprox 100 caracteres para nombre
                'Tipo_Documento': line[137:138].strip(),
                'Numero_Documento': line[138:153].strip(),   # Aprox 15 caracteres
                'Direccion_Predio': line[153:253].strip(),   # Aprox 100 caracteres para dirección
                'Destino_Economico': line[253:254].strip(),
                # Los siguientes campos numéricos suelen estar al final. 
                # Se asumen posiciones estándar, pueden requerir ajuste fino según la versión del software catastral.
                'Area_Terreno': line[254:266].strip(),
                'Area_Construida': line[266:278].strip(),
                'Avaluo': line[278:293].strip(),
                'Vigencia': line[293:297].strip() if len(line) > 297 else ''
            }
            
            # Convertir a números lo que sea posible
            try: data['Area_Terreno'] = float(data['Area_Terreno'])
            except: pass
            try: data['Area_Construida'] = float(data['Area_Construida'])
            except: pass
            try: data['Avaluo'] = float(data['Avaluo'])
            except: pass
            
            rows.append(data)
        except Exception as e:
            continue # Saltar líneas con errores de formato
            
    return pd.DataFrame(rows)

def parse_r2(file_content):
    """
    Parsea el archivo R2 (Registro 2 - Detalles Constructivos/Económicos).
    """
    rows = []
    lines = file_content.decode('utf-8', errors='ignore').split('\n')
    
    for line in lines:
        if len(line) < 50: continue
        
        try:
            # Estructura R2 suele tener el mismo ID al inicio y luego datos de construcción
            data = {
                'Codigo_Catastral_Completo': line[0:37].strip(),
                'Codigo_Adicional': line[37:50].strip(), # A veces hay códigos de construcción aquí
                # El resto de la línea en R2 contiene bloques repetitivos de calificaciones o áreas
                # Para visualización general, tomamos el resto como texto crudo o intentamos extraer valores clave
                'Datos_Variables_R2': line[50:].strip()
            }
            # Intento de extracción de avalúos o áreas adicionales si están en posiciones fijas comunes
            # Ajustado a la visualización de datos numéricos típicos en R2
            parts = line.split()
            if len(parts) > 1:
               # Buscar números grandes que parezcan avalúos al final
               pass
               
            rows.append(data)
        except:
            continue
            
    return pd.DataFrame(rows)

# --- INTERFAZ DE USUARIO ---

col1, col2 = st.columns(2)

with col1:
    r1_file = st.file_uploader("Cargar Archivo R1 (.TXT)", type=['txt'])

with col2:
    r2_file = st.file_uploader("Cargar Archivo R2 (.TXT)", type=['txt'])

if r1_file is not None:
    st.success(f"Procesando R1: {r1_file.name}")
    df_r1 = parse_r1(r1_file.getvalue())
    
    st.subheader("📋 Información de Predios (R1)")
    st.dataframe(df_r1)
    
    # Métricas rápidas
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Predios", len(df_r1))
    if 'Avaluo' in df_r1.columns and pd.api.types.is_numeric_dtype(df_r1['Avaluo']):
        c2.metric("Avalúo Total", f"${df_r1['Avaluo'].sum():,.0f}")
    
    # Filtros
    search = st.text_input("🔍 Buscar por Nombre o Cédula en R1")
    if search:
        filtered_df = df_r1[
            df_r1['Nombre_Propietario'].str.contains(search, case=False, na=False) | 
            df_r1['Numero_Documento'].str.contains(search, case=False, na=False)
        ]
        st.write("Resultados de búsqueda:")
        st.dataframe(filtered_df)

if r2_file is not None:
    st.success(f"Procesando R2: {r2_file.name}")
    df_r2 = parse_r2(r2_file.getvalue())
    
    st.subheader("🏗️ Información de Construcción/Detalle (R2)")
    st.dataframe(df_r2)

# --- UNIFICACIÓN Y DESCARGA ---

if r1_file is not None and r2_file is not None:
    st.divider()
    st.header("🔗 Datos Unificados")
    st.markdown("Se han cruzado los datos de R1 y R2 usando el **Código Catastral**.")
    
    # Unir tablas (Left join para mantener todos los predios aunque no tengan R2)
    df_merged = pd.merge(df_r1, df_r2, on='Codigo_Catastral_Completo', how='left', suffixes=('_R1', '_R2'))
    st.dataframe(df_merged)
    
    # Botón de descarga
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_merged.to_excel(writer, sheet_name='Catastro_Unificado', index=False)
        df_r1.to_excel(writer, sheet_name='R1_Crudo', index=False)
        df_r2.to_excel(writer, sheet_name='R2_Crudo', index=False)
        
    st.download_button(
        label="📥 Descargar Reporte Completo en Excel",
        data=buffer.getvalue(),
        file_name="Reporte_Catastral_Procesado.xlsx",
        mime="application/vnd.ms-excel"

    )
