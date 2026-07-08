from app import app
from models import db, Usuario

with app.app_context():

    usuario = Usuario.query.filter_by(
        correo='admin@applecosmetics.com.mx'
    ).first()

    if usuario:

        usuario.nombre = 'Uriel Luna'

        db.session.commit()

        print("Nombre actualizado correctamente")

    else:
        print("Usuario no encontrado")