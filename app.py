import os
import sys
import shutil
import time
import random
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
from config.database import create_tables, crear_admins, get_connection
from controllers.auth_controller import AuthController
from controllers.pregunta_controller import PreguntaController
from controllers.estadisticas_controller import EstadisticasController
from utils.app_config import load_app_config, save_app_config
from utils.file_loader import FileLoader
import pandas as pd
from flask import Response

# Forzar la inclusión de la carpeta raíz del proyecto en sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Configuración para usar Postgres en Render ---
# Si la variable DATABASE_URL existe (definida por Render), se le añade sslmode=require
db_url = os.getenv('DATABASE_URL')
if db_url:
    if 'sslmode' not in db_url:
        if '?' in db_url:
            db_url += '&sslmode=require'
        else:
            db_url += '?sslmode=require'
    os.environ['DATABASE_URL'] = db_url

app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = 'tu_clave_secreta'  # Cambia esto por una clave segura

def crear_examen(usuario_id):
    """
    Crea un registro en la tabla 'examenes' y retorna su ID.
    Se asume que la columna 'fecha' tiene DEFAULT CURRENT_TIMESTAMP.
    """
    conn = get_connection()
    try:
        if os.getenv("DATABASE_URL"):
            # Si estamos en PostgreSQL, usamos %s y RETURNING id
            import psycopg2.extras
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            query = "INSERT INTO examenes (usuario_id) VALUES (%s) RETURNING id"
            cursor.execute(query, (usuario_id,))
            exam_id = cursor.fetchone()["id"]
        else:
            # En SQLite usamos el placeholder ?
            cursor = conn.cursor()
            query = "INSERT INTO examenes (usuario_id) VALUES (?)"
            cursor.execute(query, (usuario_id,))
            exam_id = cursor.lastrowid
        conn.commit()
        return exam_id
    except Exception as e:
        print("Error al crear examen:", e)
        conn.rollback()
        return None
    finally:
        conn.close()

def actualizar_duracion_examen(examen_id, duracion):
    """
    Actualiza la columna 'duracion' en la tabla examenes para el examen dado.
    """
    conn = get_connection()
    try:
        if os.getenv("DATABASE_URL"):
            import psycopg2.extras
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            query = "UPDATE examenes SET duracion = %s WHERE id = %s"
            cursor.execute(query, (duracion, examen_id))
        else:
            cursor = conn.cursor()
            query = "UPDATE examenes SET duracion = ? WHERE id = ?"
            cursor.execute(query, (duracion, examen_id))
        conn.commit()
    except Exception as e:
        print("Error al actualizar duración:", e)
        conn.rollback()
    finally:
        conn.close()

def create_app():
    create_tables()
    crear_admins()

    # --- RUTA RAÍZ ---
    @app.route('/')
    def index():
        return redirect(url_for('login'))

    # --- LOGIN ---
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            correo = request.form.get('correo')
            contraseña = request.form.get('contraseña')
            if not correo or not contraseña:
                flash("Por favor, ingrese su correo y contraseña.", "error")
                return redirect(url_for('login'))
            usuario = AuthController.login(correo, contraseña)
            if usuario:
                # Aseguramos que el ID se almacene como entero para construir correctamente la URL
                session['usuario'] = {
                    'id': int(usuario.id),
                    'nombre': usuario.nombre,
                    'rol': usuario.rol,
                    'tipo_usuario': usuario.tipo_usuario
                }
                flash(f"✅ Inicio de sesión exitoso: {usuario.nombre} ({usuario.tipo_usuario})", "success")
                if usuario.rol == 'admin':
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('examen_view'))
            else:
                flash("❌ Credenciales incorrectas.", "error")
                return redirect(url_for('login'))
        return render_template('login.html')

    # --- LOGOUT ---
    @app.route('/logout')
    def logout():
        session.clear()
        flash("Sesión finalizada.", "info")
        return redirect(url_for('login'))

    # --- DASHBOARD ADMIN ---
    @app.route('/admin/dashboard')
    def admin_dashboard():
        usuario = session.get('usuario')
        if not usuario or usuario.get('rol') != 'admin':
            flash("Acceso denegado.", "error")
            return redirect(url_for('login'))
        config_data = load_app_config()
        usuarios = AuthController.listar_usuarios(usuario.get('tipo_usuario'))
        examenes = EstadisticasController.obtener_examenes_por_tipo(usuario.get('tipo_usuario'))
        active_tab = request.args.get('active_tab', 'usuarios')
        return render_template(
            'admin_dashboard.html',
            usuario=usuario,
            config_data=config_data,
            usuarios=usuarios,
            preguntas=PreguntaController.obtener_preguntas_completas_por_tipo(usuario.get('tipo_usuario')),
            examenes=examenes,
            active_tab=active_tab
        )
    
    # --- CAMBIAR CONTRASEÑA ---
    @app.route('/admin/cambiar_contraseña/<int:user_id>', methods=['GET', 'POST'])
    def cambiar_contraseña(user_id):
        usuario = session.get('usuario')
        if not usuario:
            flash("Debe iniciar sesión.", "error")
            return redirect(url_for('login'))
        if usuario['rol'] != 'admin' and usuario['id'] != user_id:
            flash("Acceso denegado.", "error")
            return redirect(url_for('login'))
        if request.method == 'POST':
            nueva_contraseña = request.form.get('nueva_contraseña')
            confirmar_contraseña = request.form.get('confirmar_contraseña')
            if not nueva_contraseña or not confirmar_contraseña:
                flash("Por favor, complete ambos campos.", "error")
                return redirect(url_for('cambiar_contraseña', user_id=user_id))
            if nueva_contraseña != confirmar_contraseña:
                flash("Las contraseñas no coinciden.", "error")
                return redirect(url_for('cambiar_contraseña', user_id=user_id))
            if len(nueva_contraseña) < 6:
                flash("La contraseña debe tener al menos 6 caracteres.", "error")
                return redirect(url_for('cambiar_contraseña', user_id=user_id))
            if AuthController.cambiar_contrasena(user_id, nueva_contraseña):
                return redirect(url_for('admin_users'))
            else:
                flash("Error al actualizar la contraseña.", "error")
                return redirect(url_for('cambiar_contraseña', user_id=user_id))
        return render_template('cambiar_contrasena.html', user_id=user_id)

    # --- EXAMEN PARA USUARIOS NO ADMIN ---
    @app.route('/examen', methods=['GET', 'POST'])
    def examen_view():
        usuario = session.get('usuario')
        if not usuario:
            flash("Debe iniciar sesión.", "error")
            return redirect(url_for('login'))
        config_data = load_app_config()
        if request.method == 'GET':
            if 'examen_id' not in session or 'preguntas_examen' not in session:
                examen_id = crear_examen(usuario['id'])
                if examen_id is None:
                    flash("Error al crear el examen.", "error")
                    return redirect(url_for('examen_view'))
                session['examen_id'] = examen_id
                session['examen_start'] = time.time()
                all_preguntas = PreguntaController.obtener_preguntas_completas_por_tipo(usuario.get('tipo_usuario'))
                random.shuffle(all_preguntas)
                max_preguntas = config_data.get('exam_params', {}).get('num_preguntas', len(all_preguntas))
                # Filtramos para quedarnos solo con las preguntas que tengan al menos una opción válida
                preguntas_validas = []
                for pregunta in all_preguntas[:max_preguntas]:
                    # Se filtran las opciones vacías o que sean '---'
                    opciones_filtradas = [op for op in pregunta.get('opciones', [])
                                        if op.get('opcion', "").strip().lower() not in ["", "---"]]
                    if opciones_filtradas:  # Solo se incluye la pregunta si tiene al menos una opción
                        nueva_pregunta = pregunta.copy()
                        nueva_pregunta['opciones'] = opciones_filtradas
                        preguntas_validas.append(nueva_pregunta)
                session['preguntas_examen'] = preguntas_validas
            # Se usa la lista filtrada para la presentación
            preguntas_presentacion = session.get('preguntas_examen', [])
            return render_template('examen_view.html', usuario=usuario, preguntas=preguntas_presentacion, config_data=config_data)
        else:
            examen_id = session.get('examen_id')
            if not examen_id:
                flash("No se encontró el examen en sesión.", "error")
                return redirect(url_for('examen_view'))
            examen_start = session.get('examen_start')
            duration = int(time.time() - examen_start) if examen_start else 0
            actualizar_duracion_examen(examen_id, duration)
            preguntas = session.get('preguntas_examen', [])
            for pregunta in preguntas:
                opcion_id = request.form.get(f"respuesta_{pregunta['id']}")
                if opcion_id:
                    PreguntaController.guardar_respuesta(examen_id, pregunta['id'], opcion_id)
            flash("Respuestas enviadas correctamente.", "success")
            session.pop('examen_id', None)
            session.pop('examen_start', None)
            session.pop('preguntas_examen', None)
            return redirect(url_for('resultados_view', exam_id=examen_id))

    # --- RESULTADOS Y ESTADÍSTICAS DEL EXAMEN ACTUAL ---
    @app.route('/resultados/<int:exam_id>')
    def resultados_view(exam_id):
        stats = EstadisticasController.obtener_estadisticas_examen(exam_id)
        return render_template('resultados_view.html', exam_id=exam_id, stats=stats)

    # --- GUARDAR PARÁMETROS DEL EXAMEN ---
    @app.route('/admin/config/guardar', methods=['POST'])
    def guardar_parametros_examen():
        usuario = session.get('usuario')
        if not usuario or usuario.get('rol') != 'admin':
            return redirect(url_for('login'))
        try:
            num_preguntas = request.form.get('num_preguntas')
            tiempo_limite = request.form.get('tiempo_limite')
            config_data = load_app_config()
            config_data.setdefault("exam_params", {})
            config_data["exam_params"]["num_preguntas"] = int(num_preguntas)
            config_data["exam_params"]["tiempo_limite"] = int(tiempo_limite)
            save_app_config(config_data)
            flash(f"Parámetros guardados: {num_preguntas} preguntas, {tiempo_limite} minutos", "success")
        except Exception as e:
            flash(f"Error al guardar parámetros: {e}", "error")
        return redirect(url_for('admin_dashboard', active_tab='config'))

    # --- RESPALDAR BD (Descargar Backup) ---
    @app.route('/admin/config/respaldo')
    def respaldar_bd():
        try:
            db_path = os.path.join(project_root, "examenes.db")
            backup_path = os.path.join(project_root, "examenes_backup.db")
            if not os.path.exists(db_path):
                flash("No se encontró la base de datos.", "error")
                return redirect(url_for('admin_dashboard', active_tab='config'))
            shutil.copy(db_path, backup_path)
            flash("Base de datos respaldada correctamente.", "success")
            return send_file(backup_path, as_attachment=True)
        except Exception as e:
            flash(f"Error al respaldar la BD: {e}", "error")
            return redirect(url_for('admin_dashboard', active_tab='config'))

    # --- RESTAURAR BD (Subir Backup) ---
    @app.route('/admin/config/restaurar', methods=['POST'])
    def restaurar_bd():
        try:
            backup_file = request.files.get('backup_file')
            if not backup_file:
                flash("No se seleccionó ningún archivo.", "error")
                return redirect(url_for('admin_dashboard', active_tab='config'))
            backup_path = os.path.join(project_root, "examenes_backup_uploaded.db")
            backup_file.save(backup_path)
            db_path = os.path.join(project_root, "examenes.db")
            shutil.copy(backup_path, db_path)
            flash("Base de datos restaurada correctamente.", "success")
        except Exception as e:
            flash(f"Error al restaurar la BD: {e}", "error")
        return redirect(url_for('admin_dashboard', active_tab='config'))

    # --- APLICAR TEMA ---
    @app.route('/admin/config/aplicar_tema', methods=['POST'])
    def aplicar_tema():
        try:
            tema = request.form.get('tema')
            config_data = load_app_config()
            config_data['tema'] = tema
            save_app_config(config_data)
            flash(f"Tema aplicado: {tema}", "success")
        except Exception as e:
            flash(f"Error al aplicar el tema: {e}", "error")
        return redirect(url_for('admin_dashboard', active_tab='config'))

    # --- ABRIR LOGS ---
    @app.route('/admin/config/abrir_logs')
    def abrir_logs():
        try:
            log_path = os.path.join(project_root, "app.log")
            if not os.path.exists(log_path):
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write("Registro de actividad:\n")
            with open(log_path, "r", encoding="utf-8") as f:
                logs = f.read()
            flash("Registros abiertos. Revisa la consola o descarga el archivo.", "info")
        except Exception as e:
            flash(f"Error al abrir los logs: {e}", "error")
        return redirect(url_for('admin_dashboard', active_tab='config'))

    # --- GUARDAR NOTIFICACIONES ---
    @app.route('/admin/config/guardar_notificaciones', methods=['POST'])
    def guardar_notificaciones():
        try:
            habilitado = request.form.get('notificaciones') == 'on'
            correo = request.form.get('correo_notif')
            config_data = load_app_config()
            config_data.setdefault('notificaciones', {})
            config_data['notificaciones']['habilitado'] = habilitado
            config_data['notificaciones']['correo'] = correo
            save_app_config(config_data)
            flash("Notificaciones guardadas.", "success")
        except Exception as e:
            flash(f"Error al guardar notificaciones: {e}", "error")
        return redirect(url_for('admin_dashboard', active_tab='config'))

    # --- SINCRONIZAR PREGUNTAS ---
    @app.route('/admin/config/sincronizar_preguntas')
    def sincronizar_preguntas():
        flash("Preguntas sincronizadas correctamente.", "success")
        return redirect(url_for('admin_dashboard', active_tab='config'))

    # --- GESTIÓN DE USUARIOS ---
    @app.route('/admin/users', methods=['GET', 'POST'])
    def admin_users():
        usuario = session.get('usuario')
        if not usuario or usuario.get('rol') != 'admin':
            return redirect(url_for('login'))
        if request.method == 'POST':
            nombre = request.form.get('nombre')
            correo = request.form.get('correo')
            contraseña = request.form.get('contraseña')
            rol = request.form.get('rol')
            localidad = request.form.get('localidad')
            if AuthController.registrar_usuario(nombre, correo, contraseña, usuario.get('tipo_usuario'), rol, localidad):
                flash("Usuario creado correctamente.", "success")
            else:
                flash("No se pudo crear el usuario.", "error")
            return redirect(url_for('admin_users'))
        usuarios = AuthController.listar_usuarios(usuario.get('tipo_usuario'))
        return render_template('admin_users.html', tipo_usuario=usuario.get('tipo_usuario'), usuarios=usuarios)

    @app.route('/admin/users/eliminar', methods=['POST'])
    def eliminar_usuario():
        usuario = session.get('usuario')
        if not usuario or usuario.get('rol') != 'admin':
            return redirect(url_for('login'))
        usuario_id = request.form.get('usuario_id')
        if usuario_id and AuthController.eliminar_usuario(int(usuario_id)):
            flash("Usuario eliminado correctamente.", "success")
        else:
            flash("No se pudo eliminar el usuario.", "error")
        return redirect(url_for('admin_users'))

    # --- GESTIÓN DE PREGUNTAS ---
    @app.route('/admin/questions', methods=['GET'])
    def admin_questions():
        usuario = session.get('usuario')
        if not usuario or usuario.get('rol') != 'admin':
            return redirect(url_for('login'))
        preguntas = PreguntaController.obtener_preguntas_completas_por_tipo(usuario.get('tipo_usuario'))
        return render_template('admin_questions.html', tipo_usuario=usuario.get('tipo_usuario'), preguntas=preguntas)

    # --- ELIMINAR PREGUNTAS ---
    @app.route('/admin/questions/eliminar', methods=['POST'])
    def eliminar_pregunta():
        usuario = session.get('usuario')
        if not usuario or usuario.get('rol') != 'admin':
            return redirect(url_for('login'))
        pregunta_id = request.form.get('pregunta_id')
        if pregunta_id and PreguntaController.eliminar_pregunta(int(pregunta_id)):
            flash("Pregunta eliminada correctamente.", "success")
        else:
            flash("No se pudo eliminar la pregunta.", "error")
        return redirect(url_for('admin_questions'))

    # --- CARGAR PREGUNTAS DESDE EXCEL ---
    @app.route('/admin/cargar_excel', methods=['GET', 'POST'])
    def cargar_excel():
        usuario = session.get('usuario')
        if not usuario or usuario.get('rol') != 'admin':
            return redirect(url_for('login'))
        if request.method == 'POST':
            excel_file = request.files.get('excel_file')
            if excel_file:
                temp_path = "temp_excel_file.xlsx"
                excel_file.save(temp_path)
                if FileLoader.cargar_preguntas_desde_excel(temp_path, usuario.get('tipo_usuario')):
                    flash("Preguntas cargadas correctamente.", "success")
                else:
                    flash("No se pudieron cargar las preguntas.", "error")
                os.remove(temp_path)
            else:
                flash("Debe seleccionar un archivo.", "error")
            return redirect(url_for('admin_questions'))
        return render_template('cargar_excel.html')
    
    @app.route('/admin/resumen_examen_usuario', methods=['GET'])
    def resumen_examen_usuario():
        """
        Interfaz para filtrar por usuario y ver, para cada examen, las preguntas
        incorrectas junto con la respuesta seleccionada y la respuesta correcta.
        Se espera un parámetro 'usuario_id' en la URL.
        Ejemplo: /admin/resumen_examen_usuario?usuario_id=2
        """
        # Verificar que el usuario autenticado sea admin
        admin = session.get('usuario')
        if not admin or admin.get('rol') != 'admin':
            flash("Acceso denegado.", "error")
            return redirect(url_for('login'))
        
        usuario_id = request.args.get('usuario_id')
        if not usuario_id:
            flash("Debes indicar un usuario a consultar.", "error")
            return redirect(url_for('admin_dashboard'))
        
        conn = get_connection()
        try:
            # Dependiendo del entorno, configurar el cursor y la consulta
            if os.getenv("DATABASE_URL"):
                import psycopg2.extras
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                query = """
                    SELECT 
                        e.id AS examen_id,
                        to_char(e.fecha AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS fecha,
                        p.id AS pregunta_id,
                        p.pregunta,
                        o1.opcion AS respuesta_seleccionada,
                        (SELECT o2.opcion 
                        FROM opciones o2 
                        WHERE o2.pregunta_id = p.id AND o2.es_correcta = true
                        LIMIT 1) AS respuesta_correcta
                    FROM respuestas r
                    JOIN examenes e ON r.examen_id = e.id
                    JOIN preguntas p ON r.pregunta_id = p.id
                    JOIN opciones o1 ON r.opcion_id = o1.id
                    WHERE e.usuario_id = %s
                    AND o1.es_correcta = false
                    ORDER BY e.fecha DESC, p.id
                """
                params = [usuario_id]
            else:
                cursor = conn.cursor()
                query = """
                    SELECT 
                        e.id AS examen_id,
                        datetime(e.fecha, 'localtime') AS fecha,
                        p.id AS pregunta_id,
                        p.pregunta,
                        o1.opcion AS respuesta_seleccionada,
                        (SELECT o2.opcion 
                        FROM opciones o2 
                        WHERE o2.pregunta_id = p.id AND o2.es_correcta = 1
                        LIMIT 1) AS respuesta_correcta
                    FROM respuestas r
                    JOIN examenes e ON r.examen_id = e.id
                    JOIN preguntas p ON r.pregunta_id = p.id
                    JOIN opciones o1 ON r.opcion_id = o1.id
                    WHERE e.usuario_id = ?
                    AND o1.es_correcta = 0
                    ORDER BY e.fecha DESC, p.id
                """
                params = [usuario_id]
            cursor.execute(query, params)
            resultados = cursor.fetchall()
        except Exception as e:
            print("Error al obtener el resumen por usuario:", e)
            flash("Ocurrió un error al obtener el resumen.", "error")
            resultados = []
        finally:
            conn.close()
        
        # Agrupar resultados por examen para facilitar la visualización
        resumen_por_examen = {}
        for r in resultados:
            exam_id = r['examen_id']
            if exam_id not in resumen_por_examen:
                resumen_por_examen[exam_id] = {
                    "fecha": r['fecha'],
                    "preguntas": []
                }
            resumen_por_examen[exam_id]["preguntas"].append({
                "pregunta_id": r['pregunta_id'],
                "pregunta": r['pregunta'],
                "respuesta_seleccionada": r['respuesta_seleccionada'],
                "respuesta_correcta": r['respuesta_correcta']
            })
        
        # Convertir a lista para pasar al template
        resumen_list = []
        for exam_id, info in resumen_por_examen.items():
            resumen_list.append({
                "examen_id": exam_id,
                "fecha": info["fecha"],
                "preguntas": info["preguntas"]
            })
        
        # Se pasa también la variable 'usuario' obtenida de la sesión
        return render_template("resumen_usuario.html", resumen=resumen_list, usuario_id=usuario_id, usuario=session.get('usuario'))
    
    @app.route('/admin/exportar_excel_resumen')
    def exportar_excel_resumen():
        """
        Exporta a Excel un resumen de las preguntas incorrectas para un usuario específico.
        Se esperan los siguientes parámetros de consulta:
        - usuario_id: ID del usuario (requerido)
        - exam_id: ID del examen (opcional)
        El resumen incluye:
        - Examen ID, Fecha, ID y enunciado de la pregunta,
        - Respuesta Seleccionada, Respuesta Correcta y el nombre del usuario.
        """
        # Verificar que el administrador esté autenticado
        usuario = session.get('usuario')
        if not usuario or usuario.get('rol') != 'admin':
            flash("Acceso denegado.", "error")
            return redirect(url_for('login'))
        
        # Obtener parámetros de consulta
        usuario_id = request.args.get('usuario_id')
        if not usuario_id:
            flash("Debe especificar un usuario para exportar.", "error")
            return redirect(url_for('resumen_examen_usuario'))
        
        exam_id_filter = request.args.get('exam_id')
        
        conn = get_connection()
        try:
            if os.getenv("DATABASE_URL"):
                # Uso de PostgreSQL
                import psycopg2.extras
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                query = """
                    SELECT 
                        e.id AS examen_id,
                        to_char(e.fecha AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS fecha,
                        p.id AS pregunta_id,
                        p.pregunta,
                        o1.opcion AS respuesta_seleccionada,
                        (SELECT o2.opcion 
                        FROM opciones o2 
                        WHERE o2.pregunta_id = p.id AND o2.es_correcta = true
                        LIMIT 1) AS respuesta_correcta,
                        u.nombre AS usuario_nombre
                    FROM respuestas r
                    JOIN examenes e ON r.examen_id = e.id
                    JOIN preguntas p ON r.pregunta_id = p.id
                    JOIN opciones o1 ON r.opcion_id = o1.id
                    JOIN usuarios u ON e.usuario_id = u.id
                    WHERE e.usuario_id = %s AND o1.es_correcta = false
                """
                params = [usuario_id]
                if exam_id_filter:
                    query += " AND e.id = %s"
                    params.append(exam_id_filter)
            else:
                # Uso de SQLite
                cursor = conn.cursor()
                query = """
                    SELECT 
                        e.id AS examen_id,
                        datetime(e.fecha, 'localtime') AS fecha,
                        p.id AS pregunta_id,
                        p.pregunta,
                        o1.opcion AS respuesta_seleccionada,
                        (SELECT o2.opcion 
                        FROM opciones o2 
                        WHERE o2.pregunta_id = p.id AND o2.es_correcta = 1
                        LIMIT 1) AS respuesta_correcta,
                        u.nombre AS usuario_nombre
                    FROM respuestas r
                    JOIN examenes e ON r.examen_id = e.id
                    JOIN preguntas p ON r.pregunta_id = p.id
                    JOIN opciones o1 ON r.opcion_id = o1.id
                    JOIN usuarios u ON e.usuario_id = u.id
                    WHERE e.usuario_id = ? AND o1.es_correcta = 0
                """
                params = [usuario_id]
                if exam_id_filter:
                    query += " AND e.id = ?"
                    params.append(exam_id_filter)
            query += " ORDER BY e.fecha DESC, p.id"
            cursor.execute(query, params)
            rows = cursor.fetchall()
        except Exception as e:
            print("Error al obtener resumen para exportación:", e)
            rows = []
        finally:
            conn.close()
        
        # Crear un DataFrame con pandas
        import pandas as pd
        if rows:
            df = pd.DataFrame(rows)
        else:
            df = pd.DataFrame(columns=["examen_id", "fecha", "pregunta_id", "pregunta", "respuesta_seleccionada", "respuesta_correcta", "usuario_nombre"])
        
        # Directorio temporal para guardar el archivo Excel
        temp_dir = os.path.join(project_root, "temp")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        file_path = os.path.join(temp_dir, "resumen_examen.xlsx")
        
        with pd.ExcelWriter(file_path, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Resumen")
        
        return send_file(
            file_path,
            as_attachment=True,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            download_name="resumen_examen.xlsx"
    )

    # --- EXPORTAR ESTADÍSTICAS A EXCEL ---
    @app.route('/admin/exportar_excel')
    def exportar_excel_calificacion():
        usuario = session.get('usuario')
        if not usuario or usuario.get('rol') != 'admin':
            flash("Acceso denegado.", "error")
            return redirect(url_for('login'))
        # Recuperar el tipo de usuario del admin
        tipo_usuario = usuario.get('tipo_usuario')
        
        filtro_usuarios = request.args.get('usuario', '')
        filtro_fecha_inicio = request.args.get('fecha_inicio', '')
        filtro_fecha_fin = request.args.get('fecha_fin', '')
        conn = get_connection()
        if os.getenv("DATABASE_URL"):
            import psycopg2.extras
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            query = """
                SELECT u.nombre, u.localidad, e.id AS examen_id, 
                    to_char(e.fecha AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS fecha,
                    e.duracion,
                    (SELECT COUNT(*) FROM respuestas r 
                        JOIN opciones o ON r.opcion_id = o.id
                        WHERE r.examen_id = e.id AND o.es_correcta = true) AS correctas,
                    (SELECT COUNT(*) FROM respuestas r 
                        JOIN opciones o ON r.opcion_id = o.id
                        WHERE r.examen_id = e.id AND o.es_correcta = false) AS incorrectas
                FROM examenes e
                JOIN usuarios u ON e.usuario_id = u.id
                WHERE u.rol = 'usuario' AND u.tipo_usuario = %s
            """
            placeholder = "%s"
            params = [tipo_usuario]
        else:
            cursor = conn.cursor()
            query = """
                SELECT u.nombre, u.localidad, e.id AS examen_id, 
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
                WHERE u.rol = 'usuario' AND u.tipo_usuario = ?
            """
            placeholder = "?"
            params = [tipo_usuario]
        
        if filtro_usuarios:
            ph = ",".join(placeholder for _ in filtro_usuarios.split(',') if _)
            query += f" AND u.nombre IN ({ph})"
            params.extend([u.strip() for u in filtro_usuarios.split(',') if u.strip()])
        if filtro_fecha_inicio and filtro_fecha_fin:
            query += " AND e.fecha BETWEEN ? AND ?"
            params.extend([filtro_fecha_inicio, filtro_fecha_fin])
        query += " ORDER BY e.fecha DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        data = []
        for row in rows:
            total_preguntas = row["correctas"] + row["incorrectas"]
            nota_final = round((row["correctas"] / total_preguntas * 10) if total_preguntas > 0 else 0, 2)
            porcentaje = round((row["correctas"] / total_preguntas * 100) if total_preguntas > 0 else 0, 2)
            duracion_min = round(row["duracion"] / 60, 2) if row["duracion"] is not None else "N/A"
            data.append({
                "Usuario": row["nombre"],
                "Localidad": row["localidad"],
                "Examen ID": row["examen_id"],
                "Fecha": row["fecha"],
                "Duración (s)": row["duracion"],
                "Duración (min)": duracion_min,
                "Correctas": row["correctas"],
                "Incorrectas": row["incorrectas"],
                "Nota Final": nota_final,
                "Porcentaje": porcentaje
            })
        df = pd.DataFrame(data)
        temp_dir = os.path.join(project_root, "temp")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        file_path = os.path.join(temp_dir, "estadisticas.xlsx")
        with pd.ExcelWriter(file_path, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Estadísticas")
        return send_file(
            file_path,
            as_attachment=True,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            download_name="estadisticas.xlsx"
        )

    @app.route('/admin/grafica/calificacion')
    def grafica_calificacion():
        # Recuperar filtros desde la URL
        usuarios_str = request.args.get('usuario', '').strip()
        lista_usuarios = [u.strip() for u in usuarios_str.split(',') if u.strip()] if usuarios_str else []
        fecha_inicio = request.args.get('fecha_inicio', '').strip()
        fecha_fin = request.args.get('fecha_fin', '').strip()
        localidad = request.args.get('localidad', '').strip()
        
        # Recuperamos el tipo de usuario del admin (OYM o LABORATORIO)
        tipo_usuario = session.get('usuario', {}).get('tipo_usuario')
        
        conn = get_connection()
        if os.getenv("DATABASE_URL"):
            import psycopg2.extras
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            query = """
                SELECT e.id AS exam_id,
                    u.nombre,
                    to_char(e.fecha AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS') AS fecha,
                    (SELECT COUNT(*) FROM respuestas r 
                        JOIN opciones o ON r.opcion_id = o.id
                        WHERE r.examen_id = e.id AND o.es_correcta = true) AS correctas,
                    (SELECT COUNT(*) FROM respuestas r 
                        JOIN opciones o ON r.opcion_id = o.id
                        WHERE r.examen_id = e.id) AS total_respuestas
                FROM examenes e
                JOIN usuarios u ON e.usuario_id = u.id
                WHERE u.tipo_usuario = %s
            """
            placeholder = "%s"
            params = [tipo_usuario]
        else:
            cursor = conn.cursor()
            query = """
                SELECT e.id AS exam_id,
                    u.nombre,
                    datetime(e.fecha, 'localtime') AS fecha,
                    (SELECT COUNT(*) FROM respuestas r 
                        JOIN opciones o ON r.opcion_id = o.id
                        WHERE r.examen_id = e.id AND o.es_correcta = 1) AS correctas,
                    (SELECT COUNT(*) FROM respuestas r 
                        JOIN opciones o ON r.opcion_id = o.id
                        WHERE r.examen_id = e.id) AS total_respuestas
                FROM examenes e
                JOIN usuarios u ON e.usuario_id = u.id
                WHERE u.tipo_usuario = ?
            """
            placeholder = "?"
            params = [tipo_usuario]
        
        # Agregar otros filtros si existen
        if lista_usuarios:
            ph = ",".join(placeholder for _ in lista_usuarios)
            query += f" AND u.nombre IN ({ph})"
            params.extend(lista_usuarios)
        if localidad:
            query += f" AND u.localidad = {placeholder}"
            params.append(localidad)
        if fecha_inicio:
            query += f" AND date(e.fecha) >= {placeholder}"
            params.append(fecha_inicio)
        if fecha_fin:
            query += f" AND date(e.fecha) <= {placeholder}"
            params.append(fecha_fin)
        query += " ORDER BY e.fecha DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        labels = []
        calificaciones = []
        if not rows:
            labels.append("No hay datos")
            calificaciones.append(0)
        else:
            for row in rows:
                total = row["total_respuestas"]
                correct = row["correctas"]
                grade = round((correct / total) * 10, 2) if total > 0 else 0.0
                labels.append(f"Examen {row['exam_id']} - {row['nombre']} - {row['fecha']}")
                calificaciones.append(grade)
            if len(rows) == 1:
                labels *= 2
                calificaciones *= 2

        data = {
            "labels": labels,
            "calificaciones": calificaciones
        }
        return jsonify(data)

    @app.route('/admin/grafica/top_incorrectas_preguntas')
    def grafica_top_incorrectas_preguntas():
        fecha_inicio = request.args.get('fecha_inicio', '').strip()
        fecha_fin = request.args.get('fecha_fin', '').strip()
        conn = get_connection()
        if os.getenv("DATABASE_URL"):
            import psycopg2.extras
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            query = """
            SELECT p.pregunta, COUNT(r.id) AS incorrectas
            FROM preguntas p
            LEFT JOIN respuestas r ON p.id = r.pregunta_id
            LEFT JOIN examenes e ON r.examen_id = e.id
            LEFT JOIN usuarios u ON e.usuario_id = u.id
            WHERE u.rol = 'usuario'
            """
        else:
            cursor = conn.cursor()
            query = """
            SELECT p.pregunta, COUNT(r.id) AS incorrectas
            FROM preguntas p
            LEFT JOIN respuestas r ON p.id = r.pregunta_id
            LEFT JOIN examenes e ON r.examen_id = e.id
            LEFT JOIN usuarios u ON e.usuario_id = u.id
            WHERE u.rol = 'usuario'
            """
        params = []
        if fecha_inicio:
            query += " AND date(e.fecha) >= ?"
            params.append(fecha_inicio)
        if fecha_fin:
            query += " AND date(e.fecha) <= ?"
            params.append(fecha_fin)
        query += " GROUP BY p.id ORDER BY incorrectas DESC LIMIT 10"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        labels = [row["pregunta"] for row in rows]
        incorrect_counts = [row["incorrectas"] for row in rows]
        return jsonify({
            "labels": labels,
            "incorrect_counts": incorrect_counts
        })

    return app

    # Importante: crea la aplicación a nivel global para que Gunicorn la encuentre.
app = create_app()

if __name__ == '__main__':
    # Detecta el entorno: 'development' para local, 'production' (u otro) para producción.
    env = os.getenv('FLASK_ENV', 'production').lower()

    if env == 'development':
        # Configuración para desarrollo local
        host = os.getenv('FLASK_RUN_HOST', '127.0.0.1')
        port = int(os.getenv('FLASK_RUN_PORT', 5000))
        debug = True  # Modo debug activado en desarrollo
    else:
        # Configuración para producción en Render: se utiliza la variable PORT
        host = os.getenv('FLASK_RUN_HOST', '0.0.0.0')
        port = int(os.getenv('PORT', 8000))
        debug = False  # Modo debug desactivado en producción

    app.run(host=host, port=port, debug=debug)
