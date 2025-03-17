import pandas as pd
import logging
from controllers.pregunta_controller import PreguntaController

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class FileLoader:
    @staticmethod
    def cargar_preguntas_desde_excel(ruta_archivo, tipo_usuario):
        """
        Carga preguntas desde un archivo Excel y las guarda en la base de datos para el tipo de usuario especificado.
        El archivo debe tener las columnas: pregunta, categoria, opcion_1, es_correcta_1, opcion_2, es_correcta_2, 
        opcion_3, es_correcta_3, opcion_4, es_correcta_4.
        """
        try:
            df = pd.read_excel(ruta_archivo)
            columnas_requeridas = {
                "pregunta", "categoria",
                "opcion_1", "es_correcta_1",
                "opcion_2", "es_correcta_2",
                "opcion_3", "es_correcta_3",
                "opcion_4", "es_correcta_4"
            }
            if not columnas_requeridas.issubset(set(df.columns)):
                logger.error("Error: El archivo debe contener las columnas requeridas.")
                return False

            total_preguntas = 0
            for _, fila in df.iterrows():
                pregunta_texto = str(fila["pregunta"]).strip()
                categoria = str(fila["categoria"]).strip()
                if pregunta_texto and categoria:
                    pregunta_id = PreguntaController.agregar_pregunta(pregunta_texto, categoria, tipo_usuario)
                    if pregunta_id:
                        for i in range(1, 5):
                            opcion = str(fila.get(f"opcion_{i}", "")).strip()
                            es_correcta = int(fila.get(f"es_correcta_{i}", 0))
                            if opcion:
                                PreguntaController.agregar_opcion(pregunta_id, opcion, es_correcta)
                        total_preguntas += 1
            logger.info(f"✅ {total_preguntas} preguntas cargadas correctamente desde el archivo.")
            return True
        except Exception as e:
            logger.error(f"❌ Error al cargar el archivo: {e}")
            return False
