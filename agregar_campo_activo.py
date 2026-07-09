import sqlite3

conexion = sqlite3.connect(
    'instance/database.db'
)

cursor = conexion.cursor()

cursor.execute("""
ALTER TABLE usuarios
ADD COLUMN activo BOOLEAN DEFAULT 1
""")

conexion.commit()

conexion.close()

print("Campo activo agregado")