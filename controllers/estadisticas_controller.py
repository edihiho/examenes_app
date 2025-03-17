from config.database import get_connection

class EstadisticasController:
    @staticmethod
    def obtener_examenes_por_tipo(tipo_usuario):
        """
        Retorna una lista de exámenes para usuarios del tipo indicado, incluyendo:
          - Nombre del usuario
          - ID del examen
          - Fecha y hora de presentación (convertida a hora local)
          - Duración del examen (en segundos)
          - Número de respuestas correctas e incorrectas
        """
        conn = get_connection()
        cursor = conn.cursor()
        query = """
        SELECT u.nombre,
               e.id AS examen_id,
               datetime(e.fecha, 'localtime') AS fecha,
               e.duracion,
               (SELECT COUNT(*) FROM respuestas r
                JOIN opciones o ON r.opcion_id = o.id
                WHERE r.examen_id = e.id AND o.es_correcta = 1) AS correctas,
               (SELECT COUNT(*) FROM respuestas r
                JOIN opciones o ON r.opcion_id = o.id
                WHERE r.examen_id = e.id AND o.es_correcta = 0) AS incorrectas
        FROM examenes e
        JOIN usuarios u ON e.usuario_id = u.id
        WHERE u.tipo_usuario = ?
        ORDER BY e.fecha DESC
        """
        cursor.execute(query, (tipo_usuario,))
        rows = cursor.fetchall()
        conn.close()
        examenes = []
        for row in rows:
            examenes.append({
                "nombre": row["nombre"],
                "examen_id": row["examen_id"],
                "fecha": row["fecha"],
                "duracion": row["duracion"] if row["duracion"] is not None else "N/A",
                "correctas": row["correctas"],
                "incorrectas": row["incorrectas"]
            })
        return examenes

    @staticmethod
    def obtener_detalles_examenes(tipo_usuario):
        """
        Retorna los detalles de cada respuesta de cada examen para usuarios del tipo indicado.
        """
        conn = get_connection()
        cursor = conn.cursor()
        query = """
        SELECT u.nombre,
               e.id AS examen_id,
               datetime(e.fecha, 'localtime') AS fecha,
               p.pregunta,
               o1.opcion AS respuesta_seleccionada,
               CASE WHEN o1.es_correcta = 1 THEN 'Correcta' ELSE 'Incorrecta' END AS estado,
               (SELECT o2.opcion FROM opciones o2 
                WHERE o2.pregunta_id = p.id AND o2.es_correcta = 1) AS respuesta_correcta
        FROM examenes e
        JOIN usuarios u ON e.usuario_id = u.id
        JOIN respuestas r ON e.id = r.examen_id
        JOIN preguntas p ON r.pregunta_id = p.id
        JOIN opciones o1 ON r.opcion_id = o1.id
        WHERE u.tipo_usuario = ?
        ORDER BY e.fecha DESC, e.id, p.id
        """
        cursor.execute(query, (tipo_usuario,))
        rows = cursor.fetchall()
        conn.close()
        detalles = []
        for row in rows:
            detalles.append({
                "nombre": row["nombre"],
                "examen_id": row["examen_id"],
                "fecha": row["fecha"],
                "pregunta": row["pregunta"],
                "respuesta_seleccionada": row["respuesta_seleccionada"],
                "estado": row["estado"],
                "respuesta_correcta": row["respuesta_correcta"]
            })
        return detalles

    @staticmethod
    def obtener_preguntas_mas_falladas(tipo_usuario):
        """
        Retorna las 5 preguntas con mayor número de respuestas incorrectas para el tipo de usuario especificado.
        """
        conn = get_connection()
        cursor = conn.cursor()
        query = """
        SELECT p.id, p.pregunta, COUNT(r.id) AS falladas
        FROM preguntas p
        LEFT JOIN respuestas r ON p.id = r.pregunta_id
        LEFT JOIN opciones o ON r.opcion_id = o.id
        WHERE p.tipo_usuario = ? AND o.es_correcta = 0
        GROUP BY p.id
        ORDER BY falladas DESC
        LIMIT 5
        """
        cursor.execute(query, (tipo_usuario,))
        rows = cursor.fetchall()
        conn.close()
        preguntas_falladas = []
        for row in rows:
            preguntas_falladas.append({
                "id": row["id"],
                "pregunta": row["pregunta"],
                "falladas": row["falladas"]
            })
        return preguntas_falladas

    @staticmethod
    def obtener_estadisticas_usuario(usuario_id):
        """
        Retorna las estadísticas totales de un usuario (acumulado de todos los exámenes).
        """
        conn = get_connection()
        cursor = conn.cursor()
        query = """
        SELECT
          (SELECT COUNT(*) FROM examenes WHERE usuario_id = ?) AS total_examenes,
          (SELECT COUNT(*) FROM respuestas r
           JOIN opciones o ON r.opcion_id = o.id
           WHERE r.examen_id IN (SELECT id FROM examenes WHERE usuario_id = ?) AND o.es_correcta = 1) AS preguntas_correctas,
          (SELECT COUNT(*) FROM respuestas r
           JOIN opciones o ON r.opcion_id = o.id
           WHERE r.examen_id IN (SELECT id FROM examenes WHERE usuario_id = ?) AND o.es_correcta = 0) AS preguntas_incorrectas
        """
        cursor.execute(query, (usuario_id, usuario_id, usuario_id))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "total_examenes": row["total_examenes"],
                "preguntas_correctas": row["preguntas_correctas"],
                "preguntas_incorrectas": row["preguntas_incorrectas"]
            }
        return None

    @staticmethod
    def obtener_estadisticas_examen(exam_id):
        """
        Retorna las estadísticas del examen específico:
          - total_respuestas: total de respuestas registradas para ese examen
          - preguntas_correctas: total de respuestas correctas
          - preguntas_incorrectas: total de respuestas incorrectas
        """
        conn = get_connection()
        cursor = conn.cursor()
        query = """
        SELECT 
          (SELECT COUNT(*) FROM respuestas WHERE examen_id = ?) AS total_respuestas,
          (SELECT COUNT(*) FROM respuestas r JOIN opciones o ON r.opcion_id = o.id WHERE examen_id = ? AND o.es_correcta = 1) AS preguntas_correctas,
          (SELECT COUNT(*) FROM respuestas r JOIN opciones o ON r.opcion_id = o.id WHERE examen_id = ? AND o.es_correcta = 0) AS preguntas_incorrectas
        """
        cursor.execute(query, (exam_id, exam_id, exam_id))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "total_respuestas": row["total_respuestas"],
                "preguntas_correctas": row["preguntas_correctas"],
                "preguntas_incorrectas": row["preguntas_incorrectas"]
            }
        return None

    @staticmethod
    def obtener_detalles_examen_por_id(exam_id):
        """
        Retorna los detalles de cada respuesta del examen especificado.
        Cada elemento contiene:
          - pregunta: Enunciado de la pregunta.
          - respuesta_seleccionada: La opción que el usuario seleccionó.
          - estado: 'Correcta' o 'Incorrecta' (según la opción seleccionada).
          - respuesta_correcta: La opción correcta para la pregunta.
        """
        conn = get_connection()
        cursor = conn.cursor()
        query = """
        SELECT p.pregunta,
               o1.opcion AS respuesta_seleccionada,
               CASE WHEN o1.es_correcta = 1 THEN 'Correcta' ELSE 'Incorrecta' END AS estado,
               (SELECT o2.opcion FROM opciones o2 
                WHERE o2.pregunta_id = p.id AND o2.es_correcta = 1) AS respuesta_correcta
        FROM respuestas r
        JOIN preguntas p ON r.pregunta_id = p.id
        LEFT JOIN opciones o1 ON r.opcion_id = o1.id
        WHERE r.examen_id = ?
        ORDER BY p.id
        """
        cursor.execute(query, (exam_id,))
        rows = cursor.fetchall()
        conn.close()
        detalles = []
        for row in rows:
            detalles.append({
                "pregunta": row["pregunta"],
                "respuesta_seleccionada": row["respuesta_seleccionada"],
                "estado": row["estado"],
                "respuesta_correcta": row["respuesta_correcta"]
            })
        return detalles

    @staticmethod
    def obtener_resumen_incorrectas_examen(exam_id):
        """
        Construye y retorna una lista con el resumen de las respuestas incorrectas para el examen.
        Cada elemento es un diccionario con:
        - pregunta: El enunciado de la pregunta.
        - respuesta_correcta: La opción correcta.
        - respuesta_usuario: La opción que el usuario seleccionó (incorrecta).
        """
        detalles = EstadisticasController.obtener_detalles_examen_por_id(exam_id)
        resumen = []
        for d in detalles:
            # Consideramos como incorrecta cualquier respuesta cuyo estado no sea 'correcta'
            if d["estado"].strip().lower() != "correcta":
                resumen.append({
                    "pregunta": d["pregunta"],
                    "respuesta_correcta": d["respuesta_correcta"],
                    "respuesta_usuario": d["respuesta_seleccionada"]
                })
        return resumen