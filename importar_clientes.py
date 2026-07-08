import pandas as pd

from app import app
from models import db, Cliente

archivo = "clientes.xlsx"

df = pd.read_excel(archivo)

with app.app_context():

    for _, fila in df.iterrows():

        cliente = Cliente(
            
            num_cliente=str(fila['Num Cliente']).strip(),
            nombre=str(fila['Nombre']).strip(),
            grupo='' if pd.isna(fila['Grupo']) else str(fila['Grupo']).strip(),
            canal='' if pd.isna(fila['Canal']) else str(fila['Canal']).strip(),
            vendedor='' if pd.isna(fila['Vendedor']) else str(fila['Vendedor']).strip()

        )

        db.session.add(cliente)

    db.session.commit()

print("Clientes importados correctamente")