import sqlite3
from config.database import get_connection

class PreguntaController:
    @staticmethod
    def agregar_pregunta(pregunta, categoria, tipo_usuario):
        """
        Inserta una pregunta en la base de datos, asignándole una categoría y el tipo de usuario (OYM o LABORATORIO).
        Retorna el ID de la pregunta insertada o None en caso de error.
        """
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO preguntas (pregunta, categoria, tipo_usuario) VALUES (?, ?, ?)',
                (pregunta, categoria, tipo_usuario)
            )
            conn.commit()
            pregunta_id = cursor.lastrowid
            return pregunta_id
        except sqlite3.Error as e:
            print("Error al agregar la pregunta:", e)
            return None
        finally:
            conn.close()

    @staticmethod
    def agregar_opcion(pregunta_id, opcion, es_correcta):
        """
        Inserta una opción de respuesta para una pregunta específica.
        'es_correcta' debe ser 1 si la opción es correcta o 0 si es incorrecta.
        Retorna el ID de la opción insertada o None en caso de error.
        """
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO opciones (pregunta_id, opcion, es_correcta) VALUES (?, ?, ?)',
                (pregunta_id, opcion, es_correcta)
            )
            conn.commit()
            opcion_id = cursor.lastrowid
            return opcion_id
        except sqlite3.Error as e:
            print("Error al agregar opción:", e)
            return None
        finally:
            conn.close()

    @staticmethod
    def obtener_preguntas():
        """
        Devuelve una lista de todas las preguntas registradas (sin opciones).
        Cada pregunta se retorna como un diccionario con sus datos.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM preguntas')
        preguntas = cursor.fetchall()
        conn.close()
        return [{
            "id": p["id"],
            "pregunta": p["pregunta"],
            "categoria": p["categoria"],
            "tipo_usuario": p["tipo_usuario"]
        } for p in preguntas]

    @staticmethod
    def obtener_preguntas_por_tipo(tipo_usuario):
        """
        Devuelve una lista de preguntas filtradas por el tipo de usuario (OYM o LABORATORIO),
        sin incluir las opciones.
        Cada pregunta se retorna como un diccionario.
        """
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM preguntas WHERE tipo_usuario = ?', (tipo_usuario,))
        preguntas = cursor.fetchall()
        conn.close()
        return [{
            "id": p["id"],
            "pregunta": p["pregunta"],
            "categoria": p["categoria"],
            "tipo_usuario": p["tipo_usuario"]
        } for p in preguntas]

    @staticmethod
    def obtener_preguntas_completas_por_tipo(tipo_usuario):
        """
        Retorna una lista de preguntas para el tipo de usuario especificado, cada una con:
          {
            "id": ...,
            "pregunta": ...,
            "categoria": ...,
            "tipo_usuario": ...,
            "opciones": [
                { "opcion": "...", "es_correcta": 0/1 },
                ...
            ]
          }
        """
        conn = get_connection()
        cursor = conn.cursor()
        # Obtener las preguntas para el tipo de usuario
        cursor.execute('''
            SELECT id, pregunta, categoria, tipo_usuario
            FROM preguntas
            WHERE tipo_usuario = ?
        ''', (tipo_usuario,))
        preguntas_raw = cursor.fetchall()

        preguntas = []
        for pr in preguntas_raw:
            pregunta_id = pr["id"]
            texto_pregunta = pr["pregunta"]
            categoria = pr["categoria"]
            t_user = pr["tipo_usuario"]

            # Obtener las opciones para la pregunta
            cursor.execute('''
                SELECT opcion, es_correcta, id FROM opciones
                WHERE pregunta_id = ?
            ''', (pregunta_id,))
            opciones_raw = cursor.fetchall()
            lista_opciones = []
            for op in opciones_raw:
                lista_opciones.append({
                    "id": op["id"],
                    "opcion": op["opcion"],
                    "es_correcta": op["es_correcta"]
                })
            preguntas.append({
                "id": pregunta_id,
                "pregunta": texto_pregunta,
                "categoria": categoria,
                "tipo_usuario": t_user,
                "opciones": lista_opciones
            })
        conn.close()
        return preguntas

    @staticmethod
    def eliminar_pregunta(id_pregunta):
        """
        Elimina una pregunta de la base de datos por su ID.
        Retorna True si se eliminó correctamente o False en caso contrario.
        """
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM preguntas WHERE id = ?', (id_pregunta,))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            print("Error al eliminar la pregunta:", e)
            return False
        finally:
            conn.close()

    @staticmethod
    def guardar_respuesta(examen_id, pregunta_id, opcion_id):
        """
        Inserta una respuesta en la base de datos para un examen dado.
        Consulta si la opción es correcta y guarda el valor (1 o 0) en la columna es_correcta.
        Retorna el ID de la respuesta insertada o None en caso de error.
        """
        conn = get_connection()
        cursor = conn.cursor()
        try:
            # Consultar si la opción es correcta
            cursor.execute("SELECT es_correcta FROM opciones WHERE id = ?", (opcion_id,))
            row = cursor.fetchone()
            es_correcta = row["es_correcta"] if row else 0
            cursor.execute(
                "INSERT INTO respuestas (examen_id, pregunta_id, opcion_id, es_correcta) VALUES (?, ?, ?, ?)",
                (examen_id, pregunta_id, opcion_id, es_correcta)
            )
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print("Error al guardar respuesta:", e)
            conn.rollback()
            return None
        finally:
            conn.close()
