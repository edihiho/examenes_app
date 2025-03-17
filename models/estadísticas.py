import sqlite3
import logging
from config.database import get_connection

# Configuración básica del logger (opcional, se puede configurar a nivel global en la app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Estadisticas:
    def __init__(self, usuario_id=None, preguntas_correctas=0, preguntas_incorrectas=0, total_examenes=0):
        self.usuario_id = usuario_id
        self.preguntas_correctas = preguntas_correctas
        self.preguntas_incorrectas = preguntas_incorrectas
        self.total_examenes = total_examenes

    @staticmethod
    def obtener_estadisticas(usuario_id):
        """Devuelve las estadísticas de un usuario."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM estadisticas WHERE usuario_id = ?', (usuario_id,))
        estadisticas = cursor.fetchone()
        conn.close()

        if estadisticas:
            return Estadisticas(
                usuario_id=estadisticas["usuario_id"],
                preguntas_correctas=estadisticas["preguntas_correctas"],
                preguntas_incorrectas=estadisticas["preguntas_incorrectas"],
                total_examenes=estadisticas["total_examenes"]
            )
        return None

# Bloque de prueba (opcional, puedes removerlo en producción)
if __name__ == "__main__":
    usuario_id = 1
    logger.info(f"📊 Estadísticas del usuario ID {usuario_id}:")
    stats = Estadisticas.obtener_estadisticas(usuario_id)

    if stats:
        logger.info(f"📌 Exámenes realizados: {stats.total_examenes}")
        logger.info(f"✅ Preguntas correctas: {stats.preguntas_correctas}")
        logger.info(f"❌ Preguntas incorrectas: {stats.preguntas_incorrectas}")
    else:
        logger.info("❌ No se encontraron estadísticas.")
