from werkzeug.security import generate_password_hash

from app import app
from models import db, Usuario

with app.app_context():

    usuario = Usuario.query.filter_by(
        correo="uriel.luna@applecosmetics.com.mx"
    ).first()

    if usuario:

        usuario.password = generate_password_hash("uri26")
        usuario.rol = "admin"

        db.session.commit()

        print("Password actualizada")

    else:
        print("No existe el usuario")