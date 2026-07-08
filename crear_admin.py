from app import app
from models import db, Usuario
from werkzeug.security import generate_password_hash

with app.app_context():

    usuario = Usuario(
        nombre="Administrador",
        correo="admin@applecosmetics.com.mx",
        password=generate_password_hash("uri26"),
        rol="admin"
    )

    db.session.add(usuario)
    db.session.commit()

    print("Administrador creado correctamente")