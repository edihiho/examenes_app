import sqlite3
import logging
import os
from config.database import get_connection

# Configuración básica del logger (puedes configurarlo globalmente en la app)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Usuario:
    def __init__(self, id=None, nombre=None, correo=None, contraseña=None, rol="usuario", tipo_usuario="OYM", localidad="Risaralda"):
        self.id = id
        self.nombre = nombre
        self.correo = correo
        self.contraseña = contraseña
        self.rol = rol
        self.tipo_usuario = tipo_usuario
        self.localidad = localidad  # Se agrega el campo localidad

    @staticmethod
    def autenticar(correo, contraseña):
        """Verifica si el correo y la contraseña son correctos."""
        conn = get_connection()
        if os.getenv("DATABASE_URL"):
            import psycopg2.extras
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            query = "SELECT * FROM usuarios WHERE correo = %s AND contraseña = %s"
        else:
            cursor = conn.cursor()
            query = "SELECT * FROM usuarios WHERE correo = ? AND contraseña = ?"
        cursor.execute(query, (correo, contraseña))
        usuario = cursor.fetchone()
        conn.close()
        if usuario:
            return Usuario(
                id=usuario["id"],
                nombre=usuario["nombre"],
                correo=usuario["correo"],
                contraseña=usuario["contraseña"],
                rol=usuario["rol"],
                tipo_usuario=usuario["tipo_usuario"],
                localidad=usuario["localidad"]
            )
        return None

    @staticmethod
    def crear_usuario(nombre, correo, contraseña, tipo_usuario, rol="usuario", localidad="Risaralda"):
        """Crea un nuevo usuario en la base de datos."""
        conn = get_connection()
        if os.getenv("DATABASE_URL"):
            import psycopg2.extras
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            query = '''
                INSERT INTO usuarios (nombre, correo, contraseña, rol, tipo_usuario, localidad) 
                VALUES (%s, %s, %s, %s, %s, %s)
            '''
        else:
            cursor = conn.cursor()
            query = '''
                INSERT INTO usuarios (nombre, correo, contraseña, rol, tipo_usuario, localidad) 
                VALUES (?, ?, ?, ?, ?, ?)
            '''
        try:
            cursor.execute(query, (nombre, correo, contraseña, rol, tipo_usuario, localidad))
            conn.commit()
            return True
        except sqlite3.IntegrityError as e:
            logger.error("Error al crear usuario: %s", e)
            return False
        finally:
            conn.close()

    @staticmethod
    def listar_usuarios(tipo_usuario):
        """Obtiene todos los usuarios del tipo especificado."""
        conn = get_connection()
        if os.getenv("DATABASE_URL"):
            import psycopg2.extras
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            query = 'SELECT id, nombre, correo, rol, tipo_usuario, localidad FROM usuarios WHERE tipo_usuario = %s'
        else:
            cursor = conn.cursor()
            query = 'SELECT id, nombre, correo, rol, tipo_usuario, localidad FROM usuarios WHERE tipo_usuario = ?'
        cursor.execute(query, (tipo_usuario,))
        usuarios = cursor.fetchall()
        conn.close()
        return [
            Usuario(
                id=u["id"],
                nombre=u["nombre"],
                correo=u["correo"],
                rol=u["rol"],
                tipo_usuario=u["tipo_usuario"],
                localidad=u["localidad"]
            ) for u in usuarios
        ]

    @staticmethod
    def eliminar_usuario(usuario_id):
        """Elimina un usuario por su ID."""
        conn = get_connection()
        if os.getenv("DATABASE_URL"):
            import psycopg2.extras
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            query = 'DELETE FROM usuarios WHERE id = %s'
        else:
            cursor = conn.cursor()
            query = 'DELETE FROM usuarios WHERE id = ?'
        cursor.execute(query, (usuario_id,))
        conn.commit()
        filas_afectadas = cursor.rowcount
        conn.close()
        return filas_afectadas > 0

    @staticmethod
    def cambiar_contrasena(user_id, nueva_contrasena):
        """
        Actualiza la contraseña del usuario con el ID proporcionado.
        Retorna True si se actualizó correctamente, False en caso contrario.
        """
        conn = get_connection()
        if os.getenv("DATABASE_URL"):
            import psycopg2.extras
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            query = "UPDATE usuarios SET contraseña = %s WHERE id = %s"
        else:
            cursor = conn.cursor()
            query = "UPDATE usuarios SET contraseña = ? WHERE id = ?"
        try:
            cursor.execute(query, (nueva_contrasena, user_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print("Error al cambiar contraseña:", e)
            conn.rollback()
            return False
        finally:
            conn.close()
