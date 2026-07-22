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
from models import Usuario, Cliente, Visita, Objetivo, Prospecto

import os
from werkzeug.utils import secure_filename

from flask import send_from_directory

from datetime import datetime
from sqlalchemy import func

from werkzeug.security import generate_password_hash

import io

from PIL import Image, ImageOps

import cloudinary.uploader

import cloudinary

cloudinary.config(
    cloud_name="fokkk3pw",
    api_key="935536672772111",
    api_secret="eVSElegD3vhdVGjzsW-9Rp2im0k",
    secure=True
)


app = Flask(__name__)

# Configuración
import os

database_url = os.getenv("DATABASE_URL")

if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://",
        "postgresql://",
        1
    )

app.config['SECRET_KEY'] = os.getenv(
    'SECRET_KEY',
    'desarrollo-local'
)

app.config['SQLALCHEMY_DATABASE_URI'] = (
    database_url or 'sqlite:///bitacora.db'
)

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
from sqlalchemy import func, extract


@app.route('/dashboard')
@login_required
def dashboard():

    hoy = datetime.now()


    # ==========================
    # ADMINISTRADOR / SUPERVISOR
    # ==========================

    if current_user.rol in ['admin', 'supervisor']:

        total_clientes = Cliente.query.count()

        total_visitas = Visita.query.count()


        visitas_mes = Visita.query.filter(
            extract('year', Visita.fecha) == hoy.year,
            extract('month', Visita.fecha) == hoy.month
        ).count()


        monto_mes = db.session.query(
            func.sum(Visita.monto_venta)
        ).filter(
            extract('year', Visita.fecha) == hoy.year,
            extract('month', Visita.fecha) == hoy.month
        ).scalar() or 0


        clientes_con_venta = db.session.query(
            Visita.cliente_id
        ).filter(
            Visita.venta_realizada.is_(True),
            extract('year', Visita.fecha) == hoy.year,
            extract('month', Visita.fecha) == hoy.month
        ).distinct().count()


        cumplimiento_vendedores = []

        usuarios = Usuario.query.filter(
            Usuario.activo == True,
            Usuario.rol == 'vendedor'
        ).all()

        for usuario in usuarios:

            objetivo_usuario = Objetivo.query.filter_by(
                usuario_id=usuario.id,
                anio=hoy.year,
                mes=hoy.month
            ).first()

            meta = objetivo_usuario.objetivo if objetivo_usuario else 0

            venta = db.session.query(
                func.sum(Visita.monto_venta)
            ).filter(
                Visita.usuario_id == usuario.id,
                extract('year', Visita.fecha) == hoy.year,
                extract('month', Visita.fecha) == hoy.month
            ).scalar() or 0

            porcentaje = 0

            if meta > 0:
                porcentaje = round(
                    (venta / meta) * 100,
                    2
                )

            cumplimiento_vendedores.append({
                'nombre': usuario.nombre,
                'meta': meta,
                'venta': venta,
                'porcentaje': porcentaje
            })

        cumplimiento_vendedores.sort(
            key=lambda x: x['porcentaje'],
            reverse=True
        )

        meta_empresa = sum(
            x['meta']
            for x in cumplimiento_vendedores
        )

        venta_empresa = sum(
            x['venta']
            for x in cumplimiento_vendedores
        )

        cumplimiento_empresa = 0

        if meta_empresa > 0:

            cumplimiento_empresa = round(
                (venta_empresa / meta_empresa) * 100,
                2
            )

        objetivo = Objetivo.query.filter_by(
            anio=hoy.year,
            mes=hoy.month
        ).first()


        cumplimiento = 0

        if objetivo and objetivo.objetivo > 0:
            cumplimiento = round(
                (monto_mes / objetivo.objetivo) * 100,
                2
            )

        prospectos_mes = Prospecto.query.filter(
            extract(
                'year',
                Prospecto.fecha_registro
            ) == hoy.year,

            extract(
                'month',
                Prospecto.fecha_registro
            ) == hoy.month
        ).count()


        return render_template(
            'dashboard.html',
            total_clientes=total_clientes,
            total_visitas=total_visitas,
            visitas_mes=visitas_mes,
            monto_mes=monto_mes,
            clientes_con_venta=clientes_con_venta,
            objetivo=objetivo.objetivo if objetivo else 0,
            cumplimiento=cumplimiento,
            meta_empresa=meta_empresa,
            venta_empresa=venta_empresa,
            cumplimiento_empresa=cumplimiento_empresa,
            cumplimiento_vendedores=cumplimiento_vendedores,
            prospectos_mes=prospectos_mes,
            admin=True
        )



    # ==========================
    # VENDEDOR
    # ==========================

    total_visitas = Visita.query.filter(
        Visita.usuario_id == current_user.id
    ).count()



    visitas_mes = Visita.query.filter(
        Visita.usuario_id == current_user.id,
        extract('year', Visita.fecha) == hoy.year,
        extract('month', Visita.fecha) == hoy.month
    ).count()



    ventas_mes = Visita.query.filter(
        Visita.usuario_id == current_user.id,
        Visita.venta_realizada.is_(True),
        extract('year', Visita.fecha) == hoy.year,
        extract('month', Visita.fecha) == hoy.month
    ).count()



    monto_mes = db.session.query(
        func.sum(Visita.monto_venta)
    ).filter(
        Visita.usuario_id == current_user.id,
        extract('year', Visita.fecha) == hoy.year,
        extract('month', Visita.fecha) == hoy.month
    ).scalar() or 0



    clientes_con_venta = db.session.query(
        Visita.cliente_id
    ).filter(
        Visita.usuario_id == current_user.id,
        Visita.venta_realizada.is_(True),
        extract('year', Visita.fecha) == hoy.year,
        extract('month', Visita.fecha) == hoy.month
    ).distinct().count()

    from datetime import date

    proximas_visitas = Visita.query.filter(
        Visita.usuario_id == current_user.id,
        Visita.proxima_visita.isnot(None),
        Visita.proxima_visita >= date.today()
    ).order_by(
        Visita.proxima_visita.asc()
    ).limit(5).all()



    objetivo = Objetivo.query.filter_by(
        usuario_id=current_user.id,
        anio=hoy.year,
        mes=hoy.month
    ).first()



    cumplimiento = 0

    if objetivo and objetivo.objetivo > 0:

        cumplimiento = round(
            (monto_mes / objetivo.objetivo) * 100,
            2
        )

    prospectos_mes = Prospecto.query.filter(
        Prospecto.usuario_id == current_user.id,

        extract(
            'year',
            Prospecto.fecha_registro
        ) == hoy.year,

        extract(
            'month',
            Prospecto.fecha_registro
        ) == hoy.month
    ).count()



    return render_template(
        'dashboard.html',
        total_visitas=total_visitas,
        visitas_mes=visitas_mes,
        ventas_mes=ventas_mes,
        monto_mes=monto_mes,
        clientes_con_venta=clientes_con_venta,
        proximas_visitas=proximas_visitas,
        objetivo=objetivo.objetivo if objetivo else 0,
        cumplimiento=cumplimiento,
        prospectos_mes=prospectos_mes,
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

    # GUARDAR CLIENTE
    if request.method == 'POST':

        existe = Cliente.query.filter_by(
            num_cliente=request.form['num_cliente']
        ).first()

        if existe:

            return '''
            <h3>
            El número de cliente ya existe.
            </h3>
            /clientes
                Regresar
            </a>
            '''

        cliente = Cliente(

            num_cliente=request.form['num_cliente'].strip(),

            nombre=request.form['nombre'].strip(),

            grupo=request.form.get(
                'grupo',
                ''
            ).strip(),

            canal=request.form.get(
                'canal',
                ''
            ).strip(),

            vendedor=request.form.get(
                'vendedor',
                ''
            ).strip()

        )

        db.session.add(cliente)

        db.session.commit()

        return redirect('/clientes')

    # BUSCADOR
    buscar = request.args.get(
        'buscar',
        ''
    )

    pagina = request.args.get(
        'page',
        1,
        type=int
    )

    if buscar:

        lista_clientes = Cliente.query.filter(

            or_(
                Cliente.num_cliente.contains(
                    buscar
                ),

                Cliente.nombre.contains(
                    buscar
                ),

                Cliente.grupo.contains(
                    buscar
                ),

                Cliente.canal.contains(
                    buscar
                )
            )

        ).order_by(
            Cliente.nombre
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

@app.route('/visita/nueva', methods=['GET', 'POST'])
@login_required
def nueva_visita():

    clientes = Cliente.query.order_by(
        Cliente.nombre
    ).all()


    if request.method == 'POST':

        archivo = request.files.get('foto')

        nombre_archivo = None


        # FOTO CLOUDINARY

        if archivo and archivo.filename:

            imagen = Image.open(archivo)


            # Corregir orientación del celular (EXIF)
            imagen = ImageOps.exif_transpose(imagen)


            # Convertir a RGB para JPEG
            if imagen.mode != "RGB":
                imagen = imagen.convert("RGB")


            imagen.thumbnail(
                (1200, 1200)
            )


            buffer = io.BytesIO()

            imagen.save(
                buffer,
                format="JPEG",
                quality=85,
                optimize=True
            )

            buffer.seek(0)


            resultado = cloudinary.uploader.upload(
                buffer,
                folder="bitacora_visitas"
            )


            nombre_archivo = resultado["secure_url"]



        proxima_visita = None


        if request.form.get('proxima_visita'):

            proxima_visita = datetime.strptime(
                request.form['proxima_visita'],
                '%Y-%m-%d'
            ).date()



        visita = Visita(

            cliente_id=request.form['cliente_id'],

            observaciones=request.form.get('observaciones'),

            venta_realizada=
                'venta_realizada' in request.form,


            monto_venta=float(
                request.form.get('monto_venta') or 0
            ),


            proxima_visita=proxima_visita,


            foto=nombre_archivo,


            latitud=request.form.get('latitud'),

            longitud=request.form.get('longitud'),


            usuario_id=current_user.id

        )


        db.session.add(visita)

        db.session.commit()


        return redirect('/visitas')



    return render_template(
        'nueva_visita.html',
        clientes=clientes
    )

@app.route('/visitas')
@login_required
def visitas():

    if current_user.rol == 'admin':

        visitas = Visita.query.order_by(
            Visita.fecha.desc()
        ).all()

    else:

        visitas = Visita.query.filter_by(
            usuario_id=current_user.id
        ).order_by(
            Visita.fecha.desc()
        ).all()


    return render_template(
        'visitas.html',
        visitas=visitas
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

from datetime import date
@app.route('/reporte_proximas_visitas')
@login_required
def reporte_proximas_visitas():

    if current_user.rol not in ['admin', 'supervisor']:
        return "Acceso denegado"

    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')

    consulta = Visita.query.filter(
        Visita.proxima_visita.isnot(None),
        Visita.proxima_visita >= date.today()
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

from datetime import date
@app.route('/mis_proximas_visitas')
@login_required
def mis_proximas_visitas():

    visitas = Visita.query.filter(
        Visita.usuario_id == current_user.id,
        Visita.proxima_visita.isnot(None),
        Visita.proxima_visita >= date.today()
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


@app.route('/objetivos')
@login_required
def objetivos():

    if current_user.rol not in ['admin', 'supervisor']:
        return redirect('/dashboard')

    objetivos = Objetivo.query.order_by(
        Objetivo.anio.desc(),
        Objetivo.mes.desc()
    ).all()

    return render_template(
        'objetivos.html',
        objetivos=objetivos
    )


@app.route('/objetivos/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_objetivo():

    if current_user.rol not in ['admin', 'supervisor']:
        return redirect('/dashboard')

    if request.method == 'POST':

        objetivo = Objetivo(
            usuario_id=request.form['usuario_id'],
            anio=request.form['anio'],
            mes=request.form['mes'],
            objetivo=request.form['objetivo']
        )

        existe = Objetivo.query.filter_by(
            usuario_id=request.form['usuario_id'],
            anio=request.form['anio'],
            mes=request.form['mes']
        ).first()

        if existe:
            return '''
            <h3>
            Ya existe un objetivo para ese usuario,
            año y mes.
            </h3>
            '''

        db.session.add(objetivo)
        db.session.commit()

        return redirect('/objetivos')

    usuarios = Usuario.query.filter_by(
        activo=True
    ).all()

    return render_template(
        'objetivo_nuevo.html',
        usuarios=usuarios
    )


@app.route('/objetivos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_objetivo(id):

    if current_user.rol not in ['admin', 'supervisor']:
        return redirect('/dashboard')

    objetivo = Objetivo.query.get_or_404(id)

    if request.method == 'POST':

        objetivo.usuario_id = request.form['usuario_id']
        objetivo.anio = request.form['anio']
        objetivo.mes = request.form['mes']
        objetivo.objetivo = request.form['objetivo']

        db.session.commit()

        return redirect('/objetivos')

    usuarios = Usuario.query.filter_by(
        activo=True
    ).all()

    return render_template(
        'editar_objetivo.html',
        objetivo=objetivo,
        usuarios=usuarios
    )


@app.route('/objetivos/eliminar/<int:id>')
@login_required
def eliminar_objetivo(id):

    if current_user.rol not in ['admin', 'supervisor']:
        return redirect('/dashboard')

    objetivo = Objetivo.query.get_or_404(id)

    db.session.delete(objetivo)
    db.session.commit()

    return redirect('/objetivos')



@app.route('/prospectos')
@login_required
def prospectos():

    if current_user.rol in ['admin', 'supervisor']:

        prospectos = Prospecto.query.order_by(
            Prospecto.fecha_registro.desc()
        ).all()

    else:

        prospectos = Prospecto.query.filter_by(
            usuario_id=current_user.id
        ).order_by(
            Prospecto.fecha_registro.desc()
        ).all()

    return render_template(
        'prospectos.html',
        prospectos=prospectos
    )

@app.route(
    '/prospectos/nuevo',
    methods=['GET', 'POST']
)
@login_required
def nuevo_prospecto():

    if request.method == 'POST':

        prospecto = Prospecto(

            nombre=request.form['nombre'],

            contacto=request.form['contacto'],

            telefono=request.form['telefono'],

            direccion=request.form['direccion'],

            observaciones=request.form['observaciones'],

            estatus=request.form['estatus'],

            usuario_id=current_user.id
        )

        db.session.add(
            prospecto
        )

        db.session.commit()

        return redirect('/prospectos')

    return render_template(
        'nuevo_prospecto.html'
    )

@app.route(
    '/prospectos/cambiar_estatus/<int:id>',
    methods=['POST']
)
@login_required
def cambiar_estatus_prospecto(id):

    prospecto = Prospecto.query.get_or_404(id)

    if (
        current_user.rol == 'vendedor'
        and prospecto.usuario_id != current_user.id
    ):
        return redirect('/prospectos')

    prospecto.estatus = request.form['estatus']

    db.session.commit()

    return redirect('/prospectos')


@app.route(
    '/prospectos/editar/<int:id>',
    methods=['GET', 'POST']
)
@login_required
def editar_prospecto(id):

    prospecto = Prospecto.query.get_or_404(id)

    if (
        current_user.rol == 'vendedor'
        and prospecto.usuario_id != current_user.id
    ):
        return redirect('/prospectos')

    if request.method == 'POST':

        prospecto.nombre = request.form['nombre']

        prospecto.contacto = request.form['contacto']

        prospecto.telefono = request.form['telefono']

        prospecto.direccion = request.form['direccion']

        prospecto.observaciones = request.form['observaciones']

        prospecto.estatus = request.form['estatus']

        db.session.commit()

        return redirect('/prospectos')

    return render_template(
        'editar_prospecto.html',
        prospecto=prospecto
    )

@app.route('/prospectos/eliminar/<int:id>')
@login_required
def eliminar_prospecto(id):

    if current_user.rol not in [
        'admin',
        'supervisor'
    ]:
        return redirect('/prospectos')

    prospecto = Prospecto.query.get_or_404(id)

    db.session.delete(prospecto)

    db.session.commit()

    return redirect('/prospectos')








UPLOAD_FOLDER = 'uploads'

app.config[
    'UPLOAD_FOLDER'
] = UPLOAD_FOLDER


app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

from models import Usuario

with app.app_context():
    print("Usuarios:", Usuario.query.count())

from models import Usuario

with app.app_context():

    usuarios = Usuario.query.all()

    for u in usuarios:
        print(
            f"ID={u.id} | Nombre={u.nombre} | Correo={u.correo} | Rol={u.rol}"
        )

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
