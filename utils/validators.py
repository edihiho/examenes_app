import re

class Validators:
    @staticmethod
    def validar_correo(correo):
        """Valida que el correo tenga un formato correcto."""
        patron = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        return re.match(patron, correo) is not None

    @staticmethod
    def validar_contraseña(contraseña):
        """Valida que la contraseña tenga al menos 6 caracteres."""
        return len(contraseña) >= 6

    @staticmethod
    def validar_texto(texto):
        """Valida que un texto no esté vacío y no sea solo espacios."""
        return bool(texto and texto.strip())

if __name__ == "__main__":
    # Pruebas de validaciones
    print("✅ Validar correo:", Validators.validar_correo("correo@example.com"))
    print("❌ Validar correo inválido:", Validators.validar_correo("correo.com"))
    print("✅ Validar contraseña segura:", Validators.validar_contraseña("123456"))
    print("❌ Validar contraseña débil:", Validators.validar_contraseña("abc"))
    print("✅ Validar texto:", Validators.validar_texto("Hola Mundo"))
    print("❌ Validar texto vacío:", Validators.validar_texto("    "))
