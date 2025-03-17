import os
import sqlite3

# Determinamos la ruta base del proyecto (un nivel arriba de la carpeta config)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_NAME = os.path.join(BASE_DIR, "examenes.db")

def get_connection():
    """Establece y retorna una conexión a la base de datos."""
    # En un entorno web, es recomendable crear una conexión nueva por cada solicitud.
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Permite acceder a columnas por nombre
    return conn

def create_tables():
    """Crea las tablas necesarias en la base de datos si no existen."""
    conn = get_connection()
    cursor = conn.cursor()

    # Tabla de usuarios
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        correo TEXT UNIQUE NOT NULL,
        contraseña TEXT NOT NULL,
        rol TEXT CHECK(rol IN ('admin', 'usuario')) NOT NULL,
        tipo_usuario TEXT CHECK(tipo_usuario IN ('OYM', 'LABORATORIO')) NOT NULL,
        localidad TEXT CHECK(localidad IN ('Risaralda', 'Quindio', 'Caldas')) NOT NULL DEFAULT 'Risaralda'
    )
    ''')

    # Agregar columna tipo_usuario si no existe
    cursor.execute("PRAGMA table_info(usuarios)")
    columnas = [col[1] for col in cursor.fetchall()]
    if "tipo_usuario" not in columnas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN tipo_usuario TEXT CHECK(tipo_usuario IN ('OYM', 'LABORATORIO')) NOT NULL DEFAULT 'OYM'")

    # Tabla de preguntas
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS preguntas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pregunta TEXT NOT NULL,
        categoria TEXT NOT NULL,
        tipo_usuario TEXT CHECK(tipo_usuario IN ('OYM', 'LABORATORIO')) NOT NULL
    )
    ''')

    # Tabla de opciones
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS opciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pregunta_id INTEGER NOT NULL,
        opcion TEXT NOT NULL,
        es_correcta BOOLEAN NOT NULL CHECK (es_correcta IN (0,1)),
        FOREIGN KEY (pregunta_id) REFERENCES preguntas(id) ON DELETE CASCADE
    )
    ''')

    # Tabla de examenes (agregamos la columna duracion para registrar el tiempo de respuesta en segundos)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS examenes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        duracion INTEGER,
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
    )
    ''')

    # Tabla de respuestas (se mantiene la restricción de NOT NULL en opcion_id; para ello se insertará una opción dummy)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS respuestas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        examen_id INTEGER NOT NULL,
        pregunta_id INTEGER NOT NULL,
        opcion_id INTEGER NOT NULL,
        es_correcta BOOLEAN NOT NULL CHECK (es_correcta IN (0,1)),
        FOREIGN KEY (examen_id) REFERENCES examenes(id) ON DELETE CASCADE,
        FOREIGN KEY (pregunta_id) REFERENCES preguntas(id) ON DELETE CASCADE,
        FOREIGN KEY (opcion_id) REFERENCES opciones(id) ON DELETE CASCADE
    )
    ''')

    conn.commit()
    conn.close()

def crear_admins():
    """Crea los administradores para OYM y LABORATORIO si no existen."""
    conn = get_connection()
    cursor = conn.cursor()

    # Crear Admin OYM
    cursor.execute("SELECT * FROM usuarios WHERE rol = 'admin' AND tipo_usuario = 'OYM'")
    admin_oym = cursor.fetchone()
    if not admin_oym:
        cursor.execute('''
        INSERT INTO usuarios (nombre, correo, contraseña, rol, tipo_usuario)
        VALUES ('Admin OYM', 'admin_oym@example.com', 'admin123', 'admin', 'OYM')
        ''')

    # Crear Admin LABORATORIO
    cursor.execute("SELECT * FROM usuarios WHERE rol = 'admin' AND tipo_usuario = 'LABORATORIO'")
    admin_lab = cursor.fetchone()
    if not admin_lab:
        cursor.execute('''
        INSERT INTO usuarios (nombre, correo, contraseña, rol, tipo_usuario)
        VALUES ('Admin LABORATORIO', 'admin_lab@example.com', 'admin123', 'admin', 'LABORATORIO')
        ''')

    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_tables()
    crear_admins()
    print("✅ Base de datos lista con administradores.")
