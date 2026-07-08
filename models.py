from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class Usuario(UserMixin, db.Model):

    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)

    nombre = db.Column(db.String(100), nullable=False)

    correo = db.Column(db.String(120), unique=True, nullable=False)

    password = db.Column(db.String(255), nullable=False)

    rol = db.Column(db.String(20), default='vendedor')



class Cliente(db.Model):

    __tablename__ = 'clientes'

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    num_cliente = db.Column(
        db.String(20),
        unique=True,
        nullable=False
    )

    nombre = db.Column(
        db.String(150),
        nullable=False
    )

    grupo = db.Column(
        db.String(100)
    )

    canal = db.Column(
        db.String(100)
    )

    vendedor = db.Column(
        db.Integer
    )

from datetime import datetime

class Visita(db.Model):

    __tablename__ = 'visitas'

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    from datetime import datetime

    fecha = db.Column(
        db.DateTime,
        default=datetime.now
    )
    

    observaciones = db.Column(
        db.Text
    )

    venta_realizada = db.Column(
        db.Boolean,
        default=False
    )

    monto_venta = db.Column(
        db.Float,
        default=0
    )

    proxima_visita = db.Column(
        db.Date
    )

    cliente_id = db.Column(
        db.Integer,
        db.ForeignKey('clientes.id')
    )

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey('usuarios.id')
    )

    latitud = db.Column(
    db.String(50)
    )

    longitud = db.Column(
    db.String(50)
    )

    foto = db.Column(
    db.String(255)
    )

    cliente = db.relationship(
        'Cliente',
        backref='visitas'
    )

    usuario = db.relationship(
        'Usuario',
        backref='visitas'
    )
