import sqlite3
import logging
from config.database import get_connection

# Configuración básica del logger (opcional, se puede configurar globalmente en la app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Pregunta:
    def __init__(self, id=None, pregunta=None, categoria=None):
        self.id = id
        self.pregunta = pregunta
        self.categoria = categoria

    @staticmethod
    def obtener_pregunta(id_pregunta):
        """Devuelve una pregunta por su ID."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM preguntas WHERE id = ?', (id_pregunta,))
        pregunta = cursor.fetchone()
        conn.close()

        if pregunta:
            return Pregunta(id=pregunta["id"], pregunta=pregunta["pregunta"], categoria=pregunta["categoria"])
        return None

    @staticmethod
    def listar_preguntas():
        """Devuelve todas las preguntas."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM preguntas')
        preguntas = cursor.fetchall()
        conn.close()

        return [Pregunta(id=p["id"], pregunta=p["pregunta"], categoria=p["categoria"]) for p in preguntas]

if __name__ == "__main__":
    logger.info("📌 Listando preguntas en la base de datos:")
    for pregunta in Pregunta.listar_preguntas():
        logger.info(f"ID: {pregunta.id} - {pregunta.pregunta} ({pregunta.categoria})")
