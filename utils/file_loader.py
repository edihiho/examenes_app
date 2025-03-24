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
        Si alguna opción está vacía, se asigna "Ninguna".
        Se procesa el valor de es_correcta sin importar mayúsculas/minúsculas y se interpreta:
         - "true" o "si" (y sus variantes) como 1.
         - "false" o "no" (y sus variantes) como 0.
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
            for index, fila in df.iterrows():
                pregunta_texto = str(fila["pregunta"]).strip()
                categoria = str(fila["categoria"]).strip()
                if pregunta_texto and categoria:
                    pregunta_id = PreguntaController.agregar_pregunta(pregunta_texto, categoria, tipo_usuario)
                    if pregunta_id:
                        for i in range(1, 5):
                            # Leer la opción y asignar "Ninguna" si está vacía.
                            opcion = str(fila.get(f"opcion_{i}", "")).strip() or "Ninguna"
                            
                            # Leer el valor de es_correcta, sin importar mayúsculas o minúsculas.
                            valor = fila.get(f"es_correcta_{i}", "")
                            es_correcta = 0  # Valor por defecto.
                            try:
                                # Si el valor es numérico, convertir a entero
                                es_int = int(valor)
                                es_correcta = 1 if es_int == 1 else 0
                            except:
                                # Si es cadena, convertir a minúsculas y comparar.
                                valor_str = str(valor).strip().lower()
                                if valor_str in ["true", "si"]:
                                    es_correcta = 1
                                elif valor_str in ["false", "no"]:
                                    es_correcta = 0
                            # Insertar la opción
                            PreguntaController.agregar_opcion(pregunta_id, opcion, es_correcta)
                        total_preguntas += 1
            logger.info(f"✅ {total_preguntas} preguntas cargadas correctamente desde el archivo.")
            return True
        except Exception as e:
            logger.error(f"❌ Error al cargar el archivo: {e}")
            return False
