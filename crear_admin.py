from werkzeug.security import generate_password_hash

from app import app
from models import db, Usuario

with app.app_context():

    admin = Usuario(

        nombre="Uriel Luna",

        correo="uriel.luna@applecosmetics.com.mx",

        password=generate_password_hash(
            "uri26"
        ),

        rol="admin",

        activo=True
    )

    db.session.add(admin)

    db.session.commit()

    print(
        "Administrador creado correctamente"
    )