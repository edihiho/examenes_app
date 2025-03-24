import os
import sqlite3
import logging
from config.database import get_connection

# Configuración básica del logger (opcional, puede configurarse globalmente en la app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Examen:
    def __init__(self, id=None, usuario_id=None, fecha=None):
        self.id = id
        self.usuario_id = usuario_id
        self.fecha = fecha

    @staticmethod
    def obtener_examen(id_examen):
        """Devuelve un examen por su ID."""
        conn = get_connection()
        if os.getenv("DATABASE_URL"):
            import psycopg2.extras
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            query = 'SELECT * FROM examenes WHERE id = %s'
        else:
            cursor = conn.cursor()
            query = 'SELECT * FROM examenes WHERE id = ?'
        cursor.execute(query, (id_examen,))
        examen = cursor.fetchone()
        conn.close()

        if examen:
            return Examen(id=examen["id"], usuario_id=examen["usuario_id"], fecha=examen["fecha"])
        return None

    @staticmethod
    def listar_examenes_usuario(usuario_id):
        """Devuelve todos los exámenes de un usuario."""
        conn = get_connection()
        if os.getenv("DATABASE_URL"):
            import psycopg2.extras
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            query = 'SELECT * FROM examenes WHERE usuario_id = %s'
        else:
            cursor = conn.cursor()
            query = 'SELECT * FROM examenes WHERE usuario_id = ?'
        cursor.execute(query, (usuario_id,))
        examenes = cursor.fetchall()
        conn.close()

        return [Examen(id=e["id"], usuario_id=e["usuario_id"], fecha=e["fecha"]) for e in examenes]

if __name__ == "__main__":
    logger.info("📌 Exámenes del usuario ID 1:")
    for examen in Examen.listar_examenes_usuario(1):
        logger.info(f"ID: {examen.id} - Fecha: {examen.fecha}")
