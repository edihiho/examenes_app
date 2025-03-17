from flask import session, redirect, url_for

def logout():
    """
    Finaliza la sesión del usuario y redirige a la pantalla de login.
    """
    session.clear()  # Elimina todos los datos de la sesión
    return redirect(url_for('login'))
