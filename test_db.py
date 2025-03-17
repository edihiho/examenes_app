# test_db.py
from config.database import get_connection

def test_insercion():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO usuarios (nombre, correo, contraseña, rol, tipo_usuario, localidad) VALUES (?, ?, ?, ?, ?, ?)",
            ("Usuario Test", "test@example.com", "test123", "usuario", "OYM", "Risaralda")
        )
        conn.commit()
        print("Inserción realizada correctamente.")
    except Exception as e:
        print("Error al insertar:", e)
    finally:
        conn.close()

if __name__ == '__main__':
    test_insercion()
