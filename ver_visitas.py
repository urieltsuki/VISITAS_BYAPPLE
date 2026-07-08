from app import app
from models import Visita

with app.app_context():

    visitas = Visita.query.all()

    print("Total visitas:", len(visitas))

    for visita in visitas:

        print("----------------")
        print("ID:", visita.id)
        print("Foto:", visita.foto)
        print("Latitud:", visita.latitud)
        print("Longitud:", visita.longitud)