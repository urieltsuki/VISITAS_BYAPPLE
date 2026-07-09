from flask import Flask
from flask import render_template
from flask import request
from flask import redirect

from flask_login import LoginManager
from flask_login import login_user
from flask_login import login_required
from flask_login import logout_user

from flask_login import current_user
from sqlalchemy import or_

from werkzeug.security import check_password_hash

from models import db
from models import Usuario, Cliente, Visita

import os
from werkzeug.utils import secure_filename

from flask import send_from_directory

from datetime import datetime
from sqlalchemy import func

from werkzeug.security import generate_password_hash


app = Flask(__name__)

# Configuración
import os

app.config['SECRET_KEY'] = os.environ.get(
    'SECRET_KEY',
    'desarrollo-local'
)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

# Base de datos
db.init_app(app)

# Crear tablas
with app.app_context():
    db.create_all()

# Flask Login
login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))


# Página principal
@app.route('/')
def inicio():
    return redirect('/login')


# Login
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        correo = request.form['correo']
        password = request.form['password']

        usuario = Usuario.query.filter_by(
            correo=correo
        ).first()

        
        if (
            usuario
            and usuario.activo
            and check_password_hash(
                usuario.password,
                password
            )
        ):


            login_user(usuario)

            return redirect('/dashboard')

        return '''
        <h3>Usuario o contraseña incorrectos</h3>
        /login
        '''

    return render_template('login.html')


# Dashboard protegido
@app.route('/dashboard')
@login_required
def dashboard():

    hoy = datetime.now()

    # ADMINISTRADOR
    if current_user.rol in ['admin', 'supervisor']:

        total_clientes = Cliente.query.count()

        total_visitas = Visita.query.count()

        visitas_mes = Visita.query.filter(
            func.strftime('%Y', Visita.fecha) == str(hoy.year),
            func.strftime('%m', Visita.fecha) == f"{hoy.month:02}"
        ).count()

        monto_mes = db.session.query(
            func.sum(Visita.monto_venta)
        ).filter(
            func.strftime('%Y', Visita.fecha) == str(hoy.year),
            func.strftime('%m', Visita.fecha) == f"{hoy.month:02}"
        ).scalar() or 0

        clientes_con_venta = db.session.query(
        Visita.cliente_id
        ).filter(
            
            Visita.venta_realizada == True,
            func.strftime('%Y', Visita.fecha) == str(hoy.year),
            func.strftime('%m', Visita.fecha) == f"{hoy.month:02}"
        ).distinct().count()

        return render_template(
            'dashboard.html',
            total_clientes=total_clientes,
            total_visitas=total_visitas,
            visitas_mes=visitas_mes,
            monto_mes=monto_mes,
            clientes_con_venta=clientes_con_venta,
            admin=current_user.rol in ['admin', 'supervisor']
        )

    # VENDEDOR
    total_visitas = Visita.query.filter(
        Visita.usuario_id == current_user.id
    ).count()

    visitas_mes = Visita.query.filter(
        Visita.usuario_id == current_user.id,
        func.strftime('%Y', Visita.fecha) == str(hoy.year),
        func.strftime('%m', Visita.fecha) == f"{hoy.month:02}"
    ).count()

    ventas_mes = Visita.query.filter(
        Visita.usuario_id == current_user.id,
        Visita.venta_realizada == True
    ).count()

    monto_mes = db.session.query(
        func.sum(Visita.monto_venta)
    ).filter(
        Visita.usuario_id == current_user.id,
        func.strftime('%Y', Visita.fecha) == str(hoy.year),
        func.strftime('%m', Visita.fecha) == f"{hoy.month:02}"
    ).scalar() or 0

    proximas_visitas = Visita.query.filter(
        Visita.usuario_id == current_user.id,
        Visita.proxima_visita != None
    ).order_by(
        Visita.proxima_visita.asc()
    ).limit(5).all()

    clientes_con_venta = db.session.query(
    Visita.cliente_id
    ).filter(
        Visita.usuario_id == current_user.id,
        Visita.venta_realizada == True,
        func.strftime('%Y', Visita.fecha) == str(hoy.year),
        func.strftime('%m', Visita.fecha) == f"{hoy.month:02}"
    ).distinct().count()

    
    return render_template(
    'dashboard.html',
    total_visitas=total_visitas,
    visitas_mes=visitas_mes,
    monto_mes=monto_mes,
    clientes_con_venta=clientes_con_venta,
    proximas_visitas=proximas_visitas,
    admin=False
)

    


# Logout
@app.route('/logout')
@login_required
def logout():

    logout_user()

    return redirect('/login')


@app.route('/clientes', methods=['GET', 'POST'])
@login_required
def clientes():

    if current_user.rol not in ['admin', 'supervisor']:
        return "Acceso denegado"

    buscar = request.args.get('buscar', '')

    pagina = request.args.get(
        'page',
        1,
        type=int
    )

    if buscar:

        lista_clientes = Cliente.query.filter(

            or_(
                Cliente.num_cliente.contains(buscar),
                Cliente.nombre.contains(buscar),
                Cliente.grupo.contains(buscar),
                Cliente.canal.contains(buscar),
                Cliente.vendedor.contains(buscar)
            )

        ).paginate(
            page=pagina,
            per_page=25,
            error_out=False
        )

    else:

        lista_clientes = Cliente.query.order_by(
            Cliente.nombre
        ).paginate(
            page=pagina,
            per_page=25,
            error_out=False
        )

    return render_template(
        'clientes.html',
        clientes=lista_clientes
    )

@app.route('/cliente/eliminar/<int:id>')
@login_required
def eliminar_cliente(id):

    if current_user.rol != 'admin':
        return "Acceso denegado"

    cliente = Cliente.query.get_or_404(id)

    db.session.delete(cliente)

    db.session.commit()

    return redirect('/clientes')

@app.route('/cliente/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_cliente(id):

    if current_user.rol != 'admin':
        return "Acceso denegado"

    cliente = Cliente.query.get_or_404(id)

    if request.method == 'POST':

        cliente.num_cliente = request.form['num_cliente']
        cliente.nombre = request.form['nombre']
        cliente.grupo = request.form['grupo']
        cliente.canal = request.form['canal']
        cliente.vendedor = request.form['vendedor']

        db.session.commit()

        return redirect('/clientes')

    return render_template(
        'editar_cliente.html',
        cliente=cliente
    )

@app.route('/visitas', methods=['GET', 'POST'])
@login_required
def visitas():

    clientes = Cliente.query.order_by(
        Cliente.nombre
    ).all()

    if request.method == 'POST':

        
        print("LATITUD:", request.form.get('latitud'))
        print("LONGITUD:", request.form.get('longitud'))


        print(request.files)

        # FOTO
        archivo = request.files.get('foto')

        nombre_archivo = None

        if archivo and archivo.filename:

            nombre_archivo = secure_filename(
                archivo.filename
            )

            archivo.save(
                os.path.join(
                    app.config['UPLOAD_FOLDER'],
                    nombre_archivo
                )
            )

        # VISITA

            proxima_visita = None

    if request.form.get('proxima_visita'):
        if not request.form.get('proxima_visita'):

            return '''
            <h3>Debe seleccionar una fecha de próxima visita</h3>
            /visitasRegresar</a>
            '''
        proxima_visita = datetime.strptime(
            request.form['proxima_visita'],
            '%Y-%m-%d'
        ).date()
        print("CLIENTE ID:", request.form.get('cliente_id'))
        visita = Visita(

            

            cliente_id=request.form['cliente_id'],

            observaciones=request.form['observaciones'],

            venta_realizada=
                'venta_realizada' in request.form,

            monto_venta=float(
                request.form['monto_venta'] or 0
            ),

            proxima_visita=proxima_visita,

            foto=nombre_archivo,

            latitud=request.form.get('latitud'),

            longitud=request.form.get('longitud'),

            usuario_id=current_user.id

        )

        print("Próxima visita:", proxima_visita)
        db.session.add(visita)

        db.session.commit()

        return redirect('/visitas')

    return render_template(
        'visitas.html',
        clientes=clientes
    )


@app.route('/historial_visitas')
@login_required
def historial_visitas():

    fecha = request.args.get('fecha', '')
    cliente = request.args.get('cliente', '')
    vendedor = request.args.get('vendedor', '')

    consulta = Visita.query

    # Solo los vendedores ven sus propias visitas
    if current_user.rol == 'vendedor':

        consulta = consulta.filter(
            Visita.usuario_id == current_user.id
        )

    # Filtro por fecha
    if fecha:

        consulta = consulta.filter(
            db.func.date(Visita.fecha) == fecha
        )

    # Filtro por cliente
    if cliente:

        consulta = consulta.join(Cliente).filter(
            Cliente.num_cliente.contains(cliente)
        )

    # Filtro por vendedor
    if (
        vendedor and
        current_user.rol in ['admin', 'supervisor']
    ):

        consulta = consulta.join(Usuario).filter(
            Usuario.nombre.contains(vendedor)
        )

    visitas = consulta.order_by(
        Visita.fecha.desc()
    ).all()

    return render_template(
        'historial_visitas.html',
        visitas=visitas
    )

@app.route('/uploads/<filename>')
def uploaded_file(filename):

    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        filename
    )

@app.route('/visita/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_visita(id):

    visita = Visita.query.get_or_404(id)

    if (
    current_user.rol == 'vendedor'
    and visita.usuario_id != current_user.id
    ):
        return "Acceso denegado"

    if request.method == 'POST':

        visita.observaciones = request.form[
            'observaciones'
        ]

        visita.venta_realizada = (
            'venta_realizada' in request.form
        )

        visita.monto_venta = float(
            request.form['monto_venta'] or 0
        )

        db.session.commit()

        return redirect('/historial_visitas')

    return render_template(
        'editar_visita.html',
        visita=visita
    )


@app.route('/usuarios', methods=['GET', 'POST'])
@login_required
def usuarios():

    if current_user.rol != 'admin':
        return "Acceso denegado"

    if request.method == 'POST':

        usuario = Usuario(

            nombre=request.form['nombre'],

            correo=request.form['correo'],

            password=generate_password_hash(
                request.form['password']
            ),

            rol=request.form['rol']

        )

        db.session.add(usuario)

        db.session.commit()

        return redirect('/usuarios')

    lista_usuarios = Usuario.query.order_by(
        Usuario.nombre
    ).all()

    return render_template(
        'usuarios.html',
        usuarios=lista_usuarios
    )

    

@app.route('/usuario/editar/<int:id>',
           methods=['GET', 'POST'])
@login_required
def editar_usuario(id):

    if current_user.rol != 'admin':
        return "Acceso denegado"

    usuario = Usuario.query.get_or_404(id)

    if request.method == 'POST':

        usuario.nombre = request.form['nombre']
        usuario.correo = request.form['correo']
        usuario.rol = request.form['rol']

        if request.form['password']:

            usuario.password = generate_password_hash(
                request.form['password']
            )

        db.session.commit()

        return redirect('/usuarios')

    return render_template(
        'editar_usuario.html',
        usuario=usuario
    )

@app.route('/usuario/eliminar/<int:id>')
@login_required
def eliminar_usuario(id):

    if current_user.rol != 'admin':
        return "Acceso denegado"

    usuario = Usuario.query.get_or_404(id)

    if usuario.id == current_user.id:
        return "No puedes eliminar tu propio usuario"

    db.session.delete(usuario)

    db.session.commit()

    return redirect('/usuarios')

@app.route('/visita/eliminar/<int:id>')
@login_required
def eliminar_visita(id):

    if current_user.rol != 'admin':
        return "Acceso denegado"

    visita = Visita.query.get_or_404(id)

    db.session.delete(visita)

    db.session.commit()

    return redirect('/historial_visitas')


@app.route('/reportes')
@login_required
def reportes():

    if current_user.rol not in ['admin', 'supervisor']:
        return "Acceso denegado"

    return render_template(
        'reportes.html'
    )

@app.route('/reporte_ventas_vendedor')
@login_required
def reporte_ventas_vendedor():

    if current_user.rol not in ['admin', 'supervisor']:
        return "Acceso denegado"

    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')

    consulta = db.session.query(

        Usuario.nombre,

        func.count(Visita.id).label('ventas'),

        func.sum(Visita.monto_venta).label('monto')

    ).join(

        Visita,
        Usuario.id == Visita.usuario_id

    ).filter(

        Visita.venta_realizada == True

    )

    if fecha_inicio:

        consulta = consulta.filter(
            db.func.date(Visita.fecha) >= fecha_inicio
        )

    if fecha_fin:

        consulta = consulta.filter(
            db.func.date(Visita.fecha) <= fecha_fin
        )

    reporte = consulta.group_by(
        Usuario.nombre
    ).all()

    total_general = sum(
        fila.monto or 0
        for fila in reporte
    )

    labels = [
        fila.nombre
        for fila in reporte
    ]

    montos = [
        float(fila.monto or 0)
        for fila in reporte
    ]

    return render_template(
        'reporte_ventas_vendedor.html',
        reporte=reporte,
        total_general=total_general,
        labels=labels,
        montos=montos
    )

@app.route('/reporte_visitas_vendedor')
@login_required
def reporte_visitas_vendedor():

    if current_user.rol not in ['admin', 'supervisor']:
        return "Acceso denegado"

    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')

    consulta = db.session.query(

        Usuario.nombre,

        func.count(Visita.id).label('visitas')

    ).join(

        Visita,
        Usuario.id == Visita.usuario_id

    )

    if fecha_inicio:

        consulta = consulta.filter(
            db.func.date(Visita.fecha) >= fecha_inicio
        )

    if fecha_fin:

        consulta = consulta.filter(
            db.func.date(Visita.fecha) <= fecha_fin
        )

    reporte = consulta.group_by(
        Usuario.nombre
    ).all()

    total_general = sum(
        fila.visitas
        for fila in reporte
    )

    labels = [
        fila.nombre
        for fila in reporte
    ]

    visitas = [
        fila.visitas
        for fila in reporte
    ]

    return render_template(
        'reporte_visitas_vendedor.html',
        reporte=reporte,
        total_general=total_general,
        labels=labels,
        visitas=visitas
    )

@app.route('/reporte_proximas_visitas')
@login_required
def reporte_proximas_visitas():

    if current_user.rol not in ['admin', 'supervisor']:
        return "Acceso denegado"

    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')

    consulta = Visita.query.filter(
        Visita.proxima_visita != None
    )

    if fecha_inicio:

        consulta = consulta.filter(
            Visita.proxima_visita >= fecha_inicio
        )

    if fecha_fin:

        consulta = consulta.filter(
            Visita.proxima_visita <= fecha_fin
        )

    visitas = consulta.order_by(
        Visita.proxima_visita.asc()
    ).all()

    return render_template(
        'reporte_proximas_visitas.html',
        visitas=visitas
    )

@app.route('/mis_proximas_visitas')
@login_required
def mis_proximas_visitas():

    visitas = Visita.query.filter(
        Visita.usuario_id == current_user.id,
        Visita.proxima_visita != None
    ).order_by(
        Visita.proxima_visita.asc()
    ).all()

    return render_template(
        'mis_proximas_visitas.html',
        visitas=visitas
    )

@app.route('/usuario/desactivar/<int:id>')
@login_required
def desactivar_usuario(id):

    if current_user.rol != 'admin':
        return "Acceso denegado"

    usuario = Usuario.query.get_or_404(id)

    if usuario.id == current_user.id:

        return (
            "No puedes "
            "desactivar tu propio usuario"
        )

    usuario.activo = False

    db.session.commit()

    return redirect('/usuarios')

@app.route('/usuario/activar/<int:id>')
@login_required
def reactivar_usuario(id):

    if current_user.rol != 'admin':
        return "Acceso denegado"

    usuario = Usuario.query.get_or_404(id)

    usuario.activo = True

    db.session.commit()

    return redirect('/usuarios')

@app.route('/cambiar_password', methods=['GET', 'POST'])
@login_required
def cambiar_password():

    mensaje = ''

    if request.method == 'POST':

        password_actual = request.form['password_actual']

        nueva_password = request.form['nueva_password']

        confirmar_password = request.form[
            'confirmar_password'
        ]

        if not check_password_hash(
            current_user.password,
            password_actual
        ):

            mensaje = 'La contraseña actual es incorrecta'

        elif nueva_password != confirmar_password:

            mensaje = 'Las contraseñas no coinciden'

        else:

            current_user.password = (
                generate_password_hash(
                    nueva_password
                )
            )

            db.session.commit()

            mensaje = 'Contraseña actualizada correctamente'

    return render_template(
        'cambiar_password.html',
        mensaje=mensaje
    )


UPLOAD_FOLDER = 'uploads'

app.config[
    'UPLOAD_FOLDER'
] = UPLOAD_FOLDER

if __name__ == '__main__':
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
