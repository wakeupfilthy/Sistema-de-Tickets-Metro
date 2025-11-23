import streamlit as st
import json
import os
import pandas as pd
from ticket_gen import * # Importamos tu lógica
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Sistema de Tickets Metro", page_icon="🚆", layout="wide")

# --- ESTILOS CSS PERSONALIZADOS ---
st.markdown("""
    <style>
    .main-header { font-size: 2rem; color: #1E3A8A; font-weight: bold; }
    .user-card { background-color: #F3F4F6; padding: 1rem; border-radius: 10px; border-left: 5px solid #1E3A8A; }
    .ticket-card { background-color: #FEF3C7; padding: 1.5rem; border-radius: 10px; border: 1px solid #F59E0B; }
    </style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN DE ESTADO (SESSION STATE) ---
if 'tickets_db' not in st.session_state:
    st.session_state.tickets_db = [] # "Base de datos" en memoria
if 'ticket_actual' not in st.session_state:
    st.session_state.ticket_actual = None
if 'paso_actual' not in st.session_state:
    st.session_state.paso_actual = "grabar" # grabar | revisar

def cargar_estados():
    try:
        with open('Estados de la incidencia.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except: return []
# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3448/3448636.png", width=80)
    st.title("Sistema Metro")
    rol_seleccionado = st.selectbox("Seleccionar Rol / Vista", ["Jefe de Estación", "Sucursal Técnica"])
    st.divider()

    if rol_seleccionado == "Jefe de Estación":
        # DATOS DEL USUARIO JEFE (Simulado ID 1)
        USUARIO_ACTUAL_ID = 1
        nombre = buscar_dato_json('Catálogo de jefes de estación.json', USUARIO_ACTUAL_ID, 'nombre_jefe_estacion')
        id_estacion = buscar_dato_json('Catálogo de jefes de estación.json', USUARIO_ACTUAL_ID, 'id_estacion')
        estacion = buscar_dato_json('Catálogo de estaciones.json', id_estacion, 'nombre_estacion')
        st.markdown("### Usuario Activo")
        st.markdown(f"**{nombre}**")
        st.caption(f"Jefe de Estación - {estacion}")
        modo = st.radio("Acciones", ["Levantamiento de Tickets", "Mis Tickets Enviados"])
    else:
        SUCURSAL_ACTUAL_ID = 1
        nombre_sucursal = buscar_dato_json('Catálogo de sucursales.json', SUCURSAL_ACTUAL_ID, 'nombre_estacion')
        ubicacion_sucursal = buscar_dato_json('Catálogo de sucursales.json', SUCURSAL_ACTUAL_ID, 'ubicacion')
        
        st.markdown(f"🏢 **{nombre_sucursal}**")
        st.caption(ubicacion_sucursal)
        modo = st.radio("Acciones", ["Gestión de Tickets", "Historial Completo"])

    st.divider()
    # Input para API KEY (Para que funcione localmente sin configurar variables de entorno)
    api_key_input = st.text_input("Google API Key", type="password")
    if api_key_input:
        os.environ["GOOGLE_API_KEY"] = api_key_input

# --- PANTALLA 1: LEVANTAMIENTO DE TICKETS ---
if rol_seleccionado == "Jefe de Estación":
    if modo == "Levantamiento de Tickets":
        st.markdown('<div class="main-header">Levantamiento de Incidencias</div>', unsafe_allow_html=True)
        st.write("Grabe un audio describiendo el problema para generar el ticket automáticamente.")

        # Pestaña 1: Grabar y Procesar
        if st.session_state.paso_actual == "grabar":
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.info("🎙️ **Instrucciones:** Mencione la falla, la ubicación específica y cualquier riesgo visible.")
                # WIDGET DE AUDIO (Nativo de Streamlit)
                audio_val = st.audio_input("Grabar reporte")

            if audio_val is not None:
                st.success("Audio capturado correctamente.")
                
                if st.button("🔍 Procesar y Generar Ticket", type="primary"):
                    if not os.environ.get("GOOGLE_API_KEY"):
                        st.error("Por favor ingrese su Google API Key en la barra lateral.")
                    else:
                        with st.spinner('Analizando audio con IA...'):
                            try:
                                # 1. Guardar audio temporalmente
                                os.makedirs("grabaciones", exist_ok=True)
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                audio_path = f"grabaciones/audio_{timestamp}.wav"
                                with open(audio_path, "wb") as f:
                                    f.write(audio_val.read())
                                audio_val.seek(0)
                                nuevo_id = 100 + len(st.session_state.tickets_db) + 1
                                ticket_obj = main(
                                    audio_path=audio_path,
                                    id_ticket=nuevo_id,
                                    id_jefe=USUARIO_ACTUAL_ID,
                                    hora=datetime.now().isoformat()
                                )
                                ticket_obj = json.loads(ticket_obj)
                                # Guardar en estado y cambiar pantalla
                                st.session_state.ticket_actual = ticket_obj
                                st.session_state.paso_actual = "revisar"
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"Error procesando el ticket: {e}")
        elif st.session_state.paso_actual == "revisar":
            t = st.session_state.ticket_actual
            st.warning(f"Confirme reporte: {t['incidencia']['nombre_incidencia']}")
            st.json(t)
            c1, c2 = st.columns(2)
            if c1.button("✅ Confirmar"):
                st.session_state.tickets_db.append(t)
                st.session_state.paso_actual = "grabar"
                st.toast("Enviado")
                st.rerun()
            if c2.button("🗑️ Descartar"):
                st.session_state.paso_actual = "grabar"
                st.rerun()

    elif modo == "Mis Tickets Enviados":
        st.subheader("Mis Reportes")
        # Filtrar solo tickets de este jefe
        mis_tickets = [t for t in st.session_state.tickets_db if t['jefe_estacion']['id_jefe'] == USUARIO_ACTUAL_ID]
        if not mis_tickets: st.info("Sin registros.")
        else:
            for t in mis_tickets:
                with st.expander(f"#{t['id_ticket']} - {t['incidencia']['nombre_incidencia']}"):
                    st.write(f"Prioridad Dinámica: {t['prioridad_dinamica']}")
                    st.write(f"Hora Reporte: {t['hora_reporte']}")
                    st.write(f"Estación: {t['estacion']['nombre_estacion']}")
                    st.write(f"Estado: {t['estado']}")
                    st.write(t['detalles_adicionales'])

# --- PANTALLA 2: SUCURSAL ---
else:
    # 1. FILTRADO DE TICKETS PARA ESTA SUCURSAL
    # Lógica: Ticket -> Estación -> ID Sucursal -> Comparar con SUCURSAL_ACTUAL_ID
    
    tickets_sucursal = []
    for t in st.session_state.tickets_db:
        id_est_ticket = t['estacion']['id_estacion']
        id_sucursal_ticket = buscar_dato_json('Catálogo de estaciones.json', id_est_ticket, 'id_sucursal')
        
        if id_sucursal_ticket == SUCURSAL_ACTUAL_ID:
            tickets_sucursal.append(t)
        else : 
            st.markdown(f"Ticket #{t['id_ticket']} pertenece a Sucursal {id_sucursal_ticket}, no a {SUCURSAL_ACTUAL_ID}")
            
    # Convertir a DataFrame para visualización
    # Aplanamos los datos anidados para la tabla
    tabla_data = []
    for t in tickets_sucursal:
        tabla_data.append({
            "prioridad_dinamica": t['prioridad_dinamica'],
            "id_ticket": t['id_ticket'],
            "nombre_incidencia": t['incidencia']['nombre_incidencia'],
            "categoria": t['incidencia']['categoria'],
            "nombre_estacion": t['estacion']['nombre_estacion'],
            "nombre_jefe": t['jefe_estacion']['nombre_jefe'],
            "estado": t['estado'],
            "hora_reporte": t['hora_reporte'], # Para historial
            "raw_ticket": t # Guardamos el objeto completo oculto para usarlo luego
        })
    
    df_tickets = pd.DataFrame(tabla_data)

    # --- PESTAÑA: GESTIÓN DE TICKETS ACTIVOS ---
    if modo == "Gestión de Tickets":
        st.markdown('<div class="main-header">Tablero de Gestión</div>', unsafe_allow_html=True)
        
        # 2. FILTRAR POR ESTADO (Ocultar Concluido, Anulado, Inconcluso)
        estados_ocultos = ["Concluido", "Anulado", "Inconcluso"]
        
        if not df_tickets.empty:
            df_activos = df_tickets[~df_tickets['estado'].isin(estados_ocultos)]
            
            # 3. ORDENAR POR PRIORIDAD (Descendente)
            df_activos = df_activos.sort_values(by='prioridad_dinamica', ascending=False)
            
            # Mostrar Tabla Resumen
            st.markdown("### 📋 Tickets Pendientes")
            columnas_visibles = ["prioridad_dinamica","hora_reporte", "id_ticket", "nombre_incidencia", "categoria", "nombre_estacion", "nombre_jefe", "estado"]
            st.dataframe(
                df_activos[columnas_visibles], 
                use_container_width=True,
                hide_index=True
            )
            
            st.divider()
            
            # SECCIÓN DE DETALLE Y EDICIÓN
            st.markdown("### 🛠️ Detalles y Acción")
            
            # Selector para elegir qué ticket trabajar
            lista_ids_activos = df_activos['id_ticket'].tolist()
            
            if lista_ids_activos:
                ticket_id_sel = st.selectbox("Seleccione ID de Ticket para gestionar:", lista_ids_activos)
                
                # Obtener el ticket seleccionado (raw data)
                ticket_sel_row = df_activos[df_activos['id_ticket'] == ticket_id_sel].iloc[0]
                ticket_full = ticket_sel_row['raw_ticket']
                
                c1, c2 = st.columns([1, 1])
                
                with c1:
                    st.markdown("#### Información del Reporte")
                    st.json(ticket_full) # Muestra todo el JSON
                    if os.path.exists(ticket_full.get('ruta_audio_descripcion', '')):
                         st.audio(ticket_full['ruta_audio_descripcion'])

                with c2:
                    st.markdown("#### Actualizar Estado")
                    st.info(f"Estado Actual: **{ticket_full['estado']}**")
                    
                    # Cargar catálogo de estados para el picklist
                    catalogo_estados = cargar_estados()
                    opciones_estados = [e['nombre'] for e in catalogo_estados]
                    
                    nuevo_estado = st.selectbox("Cambiar estado a:", opciones_estados)
                    
                    if st.button("💾 Guardar Cambio de Estado", type="primary"):
                        # BUSCAR Y ACTUALIZAR EN LA BASE DE DATOS GLOBAL
                        for i, t_db in enumerate(st.session_state.tickets_db):
                            if t_db['id_ticket'] == ticket_id_sel:
                                st.session_state.tickets_db[i]['estado'] = nuevo_estado
                                st.success(f"Ticket #{ticket_id_sel} actualizado a: {nuevo_estado}")
                                st.rerun() # Recargar para que se aplique el filtro si se cerró
            else:
                st.info("No hay tickets activos para gestionar.")
        else:
            st.success("✅ No hay tickets pendientes en esta sucursal.")

    # --- PESTAÑA: HISTORIAL COMPLETO ---
    elif modo == "Historial Completo":
        st.markdown('<div class="main-header">Historial de Sucursal</div>', unsafe_allow_html=True)
        
        if not df_tickets.empty:
            # Ordenar por fecha (descendente)
            df_historial = df_tickets.sort_values(by='hora_reporte', ascending=False)
            
            columnas_historial = ["hora_reporte", "id_ticket", "nombre_incidencia", "nombre_estacion", "estado"]
            
            st.dataframe(
                df_historial[columnas_historial],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("El historial está vacío.")