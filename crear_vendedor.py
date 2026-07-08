from app import app
from models import db, Usuario
from werkzeug.security import generate_password_hash

with app.app_context():

    vendedor = Usuario(
        nombre="Vendedor Prueba",
        correo="vendedor@empresa.com",
        password=generate_password_hash("123456"),
        rol="vendedor"
    )

    db.session.add(vendedor)
    db.session.commit()

    print("Vendedor creado")