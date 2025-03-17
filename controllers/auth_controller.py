from flask import flash
from models.usuario import Usuario

class AuthController:
    @staticmethod
    def login(correo, contraseña):
        usuario = Usuario.autenticar(correo, contraseña)
        if usuario:
            flash(f"✅ Inicio de sesión exitoso: {usuario.nombre} ({usuario.tipo_usuario})", "success")
            return usuario
        else:
            flash("❌ Credenciales incorrectas.", "error")
            return None

    @staticmethod
    def registrar_usuario(nombre, correo, contraseña, tipo_usuario, rol="usuario", localidad=None):
        if tipo_usuario not in ["OYM", "LABORATORIO"]:
            flash(f"❌ Tipo de usuario inválido: {tipo_usuario}.", "error")
            return False
        exito = Usuario.crear_usuario(nombre, correo, contraseña, tipo_usuario, rol, localidad)
        if exito:
            flash("✅ Usuario registrado correctamente.", "success")
            return True
        else:
            flash("❌ No se pudo registrar el usuario (correo duplicado o error).", "error")
            return False

    @staticmethod
    def listar_usuarios(tipo_usuario):
        return Usuario.listar_usuarios(tipo_usuario)

    @staticmethod
    def eliminar_usuario(usuario_id):
        exito = Usuario.eliminar_usuario(usuario_id)
        if exito:
            flash(f"✅ Usuario con ID {usuario_id} eliminado correctamente.", "success")
            return True
        else:
            flash(f"❌ No se pudo eliminar el usuario con ID {usuario_id}.", "error")
            return False

    @staticmethod
    def cambiar_contrasena(user_id, nueva_contrasena):
        exito = Usuario.cambiar_contrasena(user_id, nueva_contrasena)
        if exito:
            flash("✅ Contraseña actualizada correctamente.", "success")
        else:
            flash("❌ Error al actualizar la contraseña.", "error")
        return exito
