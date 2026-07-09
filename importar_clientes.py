import pandas as pd

from app import app
from models import db, Cliente

ARCHIVO = "Clientes.xlsx"

with app.app_context():

    df = pd.read_excel(ARCHIVO)

    print(f"Registros encontrados: {len(df)}")

    clientes = []

    for _, fila in df.iterrows():

        cliente = Cliente(
            num_cliente=str(fila['Num Cliente']).strip(),
            nombre=str(fila['Nombre']).strip(),
            grupo=str(fila['Grupo']).strip() if pd.notna(fila['Grupo']) else None,
            canal=str(fila['Canal']).strip() if pd.notna(fila['Canal']) else None,
            vendedor=int(fila['Vendedor']) if pd.notna(fila['Vendedor']) else None
        )

        clientes.append(cliente)

    db.session.bulk_save_objects(clientes)
    db.session.commit()

    print(f"Clientes importados: {len(clientes)}")