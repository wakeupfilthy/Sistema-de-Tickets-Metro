from google import genai
from google.genai import types
import json

client = genai.Client(api_key="AIzaSyCJWfml5Y4HXplIlq91l436Z5Y6VUHnUrQ")

def buscar_dato_json(archivo, id_buscado, campo_buscado):
    with open(archivo, 'r', encoding='utf-8') as archivo:
        datos = json.load(archivo)

    incidencia = next((item for item in datos if item["id"] == id_buscado), None)

    if incidencia:
        return incidencia.get(campo_buscado, None)
    return None

def calcular_bonificador_tiempo(tiempo_total, id_incidencia):
    """
    Calcula el bonificador de tiempo (Time Stress Bonus) basado en la holgura
    restante y ajusta la prioridad final para asegurar la atención a tiempo.
    """
    tiempo_viaje = buscar_dato_json('Catálogo de estaciones.json', id_incidencia, 'tiempo_viaje_aproximado')
    tiempo_reparacion = buscar_dato_json('Catálogo de incidencias.json', id_incidencia, 'tiempo_estimado_reparacion')
    nivel_prioridad = buscar_dato_json('Catálogo de incidencias.json', id_incidencia, 'nivel_prioridad')
    tiempo_holgura=(tiempo_total-tiempo_viaje-tiempo_reparacion)
    bonificador = 0

    if tiempo_holgura <= 15:
        # Punto de No Retorno: El tiempo es CRÍTICO, forzamos la prioridad MÁXIMA.
        bonificador = 5 - nivel_prioridad  # Ajuste para que la suma sea 5
        if bonificador < 0:
            bonificador = 0 # Evita que reste, pero la prioridad final siempre será 5
        
        # Si la holgura es negativa (ya estamos tarde), el bonificador es el máximo.
        if tiempo_holgura < 0:
             bonificador = 5 - nivel_prioridad
             if bonificador < 0:
                 bonificador = 0
    elif 15 < tiempo_holgura <= 30:
        # Zona Naranja: Alta presión, el riesgo de multa es inminente.
        bonificador = 2
    
    elif 30 < tiempo_holgura <= 60:
        # Zona Amarilla: Presión moderada, necesita subir un escalón.
        bonificador = 1
    
    elif tiempo_holgura > 60:
        # Zona Verde: Tiempo suficiente.
        bonificador = 0

    # Calculamos la prioridad dinámica final, asegurando que no exceda 5
    prioridad_dinamica_calculada = nivel_prioridad + bonificador
    
    # Aseguramos que el valor no sobrepase 5
    if prioridad_dinamica_calculada > 5:
        prioridad_dinamica_calculada = 5

    return prioridad_dinamica_calculada

def procesar_audio(audio_path, Prompt_Audio):
    with open(audio_path, "rb") as audio_file:
        audio_bytes = audio_file.read()

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"),
            Prompt_Audio
        ],
    )
    return response.text

def obtener_incidencia_gemini(prompt):
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        # Intentar transofrmar la respuesta a entero y retornarlo
    try:
        categoria_id = int(response.text.strip())
        return categoria_id
    except ValueError:
        raise Exception(f"Respuesta inesperada del modelo: {response.text}")
    
def generate_ticket(id_ticket, id_incidencia, hora, id_jefe, detalles, notas_adicionales, ruta_audio):
    #Datos del catalogo de incidencias
    nombre_incidencia = buscar_dato_json('Catálogo de incidencias.json', id_incidencia, 'nombre_incidencia')
    categoria = buscar_dato_json('Catálogo de incidencias.json', id_incidencia, 'categoria')
    urgencia = buscar_dato_json('Catálogo de incidencias.json', id_incidencia, 'nivel_prioridad')
    #Datos del catalogo de jefe de estacion
    id_estacion = buscar_dato_json('Catálogo de jefes de estación.json', id_jefe, 'id_estacion')
    nombre_jefe = buscar_dato_json('Catálogo de jefes de estación.json', id_jefe, 'nombre_jefe_estacion')
    contacto_jefe = buscar_dato_json('Catálogo de jefes de estación.json', id_jefe, 'contacto_jefe_estacion')
    #Datos del catalogo de estaciones
    nombre_estacion = buscar_dato_json('Catálogo de estaciones.json', id_estacion, 'nombre_estacion')
    #Datos del catalogo de estados
    estado = buscar_dato_json('Estados de la incidencia.json', 1, 'nombre')
    prioridad = calcular_bonificador_tiempo(120, id_incidencia)
    #Construir ticket
    ticket = {
        "id_ticket": id_ticket,
        "incidencia": {
            "id_incidencia": id_incidencia,
            "nombre_incidencia": nombre_incidencia,
            "categoria": categoria,
            "urgencia": urgencia
        },
        "hora_reporte": hora,
        "jefe_estacion": {
            "id_jefe": id_jefe,
            "nombre_jefe": nombre_jefe,
            "contacto_jefe": contacto_jefe
        },
        "estacion": {
            "id_estacion": id_estacion,
            "nombre_estacion": nombre_estacion
        },
        "estado": estado,
        "prioridad_dinamica": prioridad,
        "detalles_adicionales": detalles,
        "notas_adicionales": notas_adicionales,
        "ruta_audio_descripcion": ruta_audio
    }
    return ticket

def generar_prompt_clasificacion(catalogo_json, description):
    Prompt = f'''
    Analiza el siguiente texto de incidencia y clasifícalo utilizando el catálogo proporcionado. Como respuesta, genera únicamente el número entero (ID) de la categoría más relevante, sin ningún texto o formato JSON adicional.

    Las categorías y sus IDs son:

    {catalogo_json}

    Texto de incidencia a clasificar: {description}

    Formato de Salida Requerido:

    [ID DE LA CATEGORÍA RELACIONADA -SOLO EL NÚMERO]
    '''
    return Prompt

def main(audio_path, id_ticket, id_jefe, hora):
    Prompt_Audio = f'''
    Escucha atentamente el audio proporcionado y transcribe lo que dice el usuario.
    '''
    description = procesar_audio(audio_path, Prompt_Audio)
    catalogo_lista = [
    { "id": 1, "nombre_incidencia": "Bloqueo de puertas de vagón" },
    { "id": 2, "nombre_incidencia": "Falla de aire acondicionado en vagón" },
    { "id": 3, "nombre_incidencia": "Zapatas de freno pegadas" },
    { "id": 4, "nombre_incidencia": "Falla en sistema de megafonía del tren" },
    { "id": 5, "nombre_incidencia": "Falso en circuito de vía" },
    { "id": 6, "nombre_incidencia": "Falla en cambio de vía" },
    { "id": 7, "nombre_incidencia": "Pérdida de comunicación tren-control" },
    { "id": 8, "nombre_incidencia": "Semáforo defectusoso" },
    { "id": 9, "nombre_incidencia": "Fisura en riel" },
    { "id": 10, "nombre_incidencia": "Objeto en vías" },
    { "id": 11, "nombre_incidencia": "Filtración de agua en túnel" },
    { "id": 12, "nombre_incidencia": "Sujeción de vía suelto" },
    { "id": 13, "nombre_incidencia": "Corte de tensión en catenaria" },
    { "id": 14, "nombre_incidencia": "Disparo de interruptor en subestación" },
    { "id": 15, "nombre_incidencia": "Falla en alumbrado de túnel" },
    { "id": 16, "nombre_incidencia": "Recalentamiento en transformador auxiliar" },
    { "id": 17, "nombre_incidencia": "Escalera mecánica detenida" },
    { "id": 18, "nombre_incidencia": "Atrapamiento en ascensor" },
    { "id": 19, "nombre_incidencia": "Torniquete de entrada atascado" },
    { "id": 20, "nombre_incidencia": "Máquina expendedora fuera de servicio" },
    { "id": 21, "nombre_incidencia": "otros" }
    ]
    
    catalogo_json = json.dumps(catalogo_lista, indent=2, ensure_ascii=False)
    Prompt = generar_prompt_clasificacion(catalogo_json, description)
    id_incidencia_1 = obtener_incidencia_gemini(Prompt)
    # Generar ticket
    # To do: generar ID automático, hora actual automática
    ticket_generado = generate_ticket(
        id_ticket=id_ticket,
        id_incidencia=id_incidencia_1,
        hora=hora,
        id_jefe=id_jefe,
        detalles=description,
        notas_adicionales="",
        ruta_audio=audio_path
    )
    #convertir a JSON para visualizar mejor
    ticket_json = json.dumps(ticket_generado, indent=2, ensure_ascii=False)
    return ticket_json