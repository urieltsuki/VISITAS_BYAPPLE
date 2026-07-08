from app import app
from models import db, Usuario
from werkzeug.security import generate_password_hash

with app.app_context():

    usuario = Usuario.query.filter_by(
        correo='admin@empresa.com'
    ).first()

    if usuario:

        usuario.correo = 'admin@applecosmetics.com.mx'

        usuario.password = generate_password_hash(
            'uri26'
        )

        db.session.commit()

        print("Administrador actualizado")

    else:
        print("Usuario no encontrado")