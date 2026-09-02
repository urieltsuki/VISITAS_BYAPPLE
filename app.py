from flask import Flask, render_template, request, redirect, url_for

from flask_login import LoginManager
from flask_login import login_user
from flask_login import login_required
from flask_login import logout_user

from flask_login import current_user
from sqlalchemy import or_

from werkzeug.security import check_password_hash

from models import db
from models import Usuario, Cliente, Visita, Objetivo, Prospecto, Llamada

import os
from werkzeug.utils import secure_filename

from flask import send_from_directory

from datetime import datetime, date, timedelta
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

    from datetime import datetime

    ahora = datetime.now()

    inicio_mes = datetime(
        ahora.year,
        ahora.month,
        1
    )

    # ==========================================
    # VARIABLES GENERALES
    # ==========================================

    admin = current_user.rol in ['admin', 'supervisor']


    # ==========================================
    # CLIENTES
    # ==========================================

    if current_user.rol == 'vendedor':

        clientes_total = Cliente.query.filter(
            Cliente.vendedor == current_user.id
        ).count()

    else:

        clientes_total = Cliente.query.count()


    # ==========================================
    # VISITAS
    # ==========================================

    if current_user.rol == 'vendedor':

        visitas_total = Visita.query.filter(
            Visita.usuario_id == current_user.id
        ).count()

        visitas_mes = Visita.query.filter(
            Visita.usuario_id == current_user.id,
            Visita.fecha >= inicio_mes
        ).count()

    else:

        visitas_total = Visita.query.count()

        visitas_mes = Visita.query.filter(
            Visita.fecha >= inicio_mes
        ).count()


    # ==========================================
    # PROSPECTOS
    # ==========================================

    if current_user.rol == 'vendedor':

        prospectos_mes = Prospecto.query.filter(
            Prospecto.usuario_id == current_user.id,
            Prospecto.fecha_registro >= inicio_mes
        ).count()

    else:

        prospectos_mes = Prospecto.query.filter(
            Prospecto.fecha_registro >= inicio_mes
        ).count()


    # ==========================================
    # LLAMADAS
    # ==========================================

    if current_user.rol == 'vendedor':

        llamadas_mes = Llamada.query.filter(
            Llamada.usuario_id == current_user.id,
            Llamada.fecha >= inicio_mes
        ).count()

    else:

        llamadas_mes = Llamada.query.filter(
            Llamada.fecha >= inicio_mes
        ).count()


    # ==========================================
    # VENTAS POR VISITAS
    # ==========================================

    if current_user.rol == 'vendedor':

        ventas_visitas = db.session.query(
            db.func.sum(Visita.monto_venta)
        ).filter(
            Visita.usuario_id == current_user.id,
            Visita.fecha >= inicio_mes,
            Visita.monto_venta > 0
        ).scalar() or 0

    else:

        ventas_visitas = db.session.query(
            db.func.sum(Visita.monto_venta)
        ).filter(
            Visita.fecha >= inicio_mes,
            Visita.monto_venta > 0
        ).scalar() or 0


    # ==========================================
    # VENTAS POR LLAMADAS
    # ==========================================

    if current_user.rol == 'vendedor':

        ventas_llamadas = db.session.query(
            db.func.sum(Llamada.monto_venta)
        ).filter(
            Llamada.usuario_id == current_user.id,
            Llamada.fecha >= inicio_mes,
            Llamada.monto_venta > 0
        ).scalar() or 0

    else:

        ventas_llamadas = db.session.query(
            db.func.sum(Llamada.monto_venta)
        ).filter(
            Llamada.fecha >= inicio_mes,
            Llamada.monto_venta > 0
        ).scalar() or 0


    # ==========================================
    # VENTA TOTAL DEL MES
    # VISITAS + LLAMADAS
    # ==========================================

    venta_mes = (
        ventas_visitas +
        ventas_llamadas
    )


    # ==========================================
    # CLIENTES ÚNICOS CON VENTA
    # ==========================================

    if current_user.rol == 'vendedor':

        clientes_venta_visitas = db.session.query(
            Visita.cliente_id
        ).filter(
            Visita.usuario_id == current_user.id,
            Visita.fecha >= inicio_mes,
            Visita.monto_venta > 0
        ).all()


        clientes_venta_llamadas = db.session.query(
            Llamada.cliente_id
        ).filter(
            Llamada.usuario_id == current_user.id,
            Llamada.fecha >= inicio_mes,
            Llamada.monto_venta > 0
        ).all()

    else:

        clientes_venta_visitas = db.session.query(
            Visita.cliente_id
        ).filter(
            Visita.fecha >= inicio_mes,
            Visita.monto_venta > 0
        ).all()


        clientes_venta_llamadas = db.session.query(
            Llamada.cliente_id
        ).filter(
            Llamada.fecha >= inicio_mes,
            Llamada.monto_venta > 0
        ).all()


    clientes_con_venta_ids = set()


    for resultado in clientes_venta_visitas:

        if resultado[0] is not None:

            clientes_con_venta_ids.add(
                resultado[0]
            )


    for resultado in clientes_venta_llamadas:

        if resultado[0] is not None:

            clientes_con_venta_ids.add(
                resultado[0]
            )


    clientes_con_venta = len(
        clientes_con_venta_ids
    )


    # ==========================================
    # OBJETIVO Y RANKING
    # ==========================================

    meta_empresa = 0
    venta_empresa = 0
    cumplimiento_empresa = 0

    cumplimiento_vendedores = []


    # ==========================================
    # ADMIN / SUPERVISOR
    # ==========================================

    if admin:

        vendedores = Usuario.query.filter(
            Usuario.rol == 'vendedor',
            Usuario.activo == True
        ).all()

        for vendedor in vendedores:

            # ------------------------------
            # OBJETIVO DEL VENDEDOR
            # ------------------------------

            objetivo = Objetivo.query.filter(
                Objetivo.usuario_id == vendedor.id,
                Objetivo.anio == ahora.year,
                Objetivo.mes == ahora.month
            ).first()

            meta = objetivo.objetivo if objetivo else 0


            # ------------------------------
            # VENTAS POR VISITAS
            # ------------------------------

            venta_visitas_vendedor = db.session.query(
                db.func.sum(Visita.monto_venta)
            ).filter(
                Visita.usuario_id == vendedor.id,
                Visita.fecha >= inicio_mes,
                Visita.monto_venta > 0
            ).scalar() or 0


            # ------------------------------
            # VENTAS POR LLAMADAS
            # ------------------------------

            venta_llamadas_vendedor = db.session.query(
                db.func.sum(Llamada.monto_venta)
            ).filter(
                Llamada.usuario_id == vendedor.id,
                Llamada.fecha >= inicio_mes,
                Llamada.monto_venta > 0
            ).scalar() or 0


            # ------------------------------
            # VENTA TOTAL DEL VENDEDOR
            # ------------------------------

            venta = (
                venta_visitas_vendedor +
                venta_llamadas_vendedor
            )


            # ------------------------------
            # CUMPLIMIENTO
            # ------------------------------

            if meta > 0:

                porcentaje = round(
                    (venta / meta) * 100,
                    1
                )

            else:

                porcentaje = 0


            cumplimiento_vendedores.append({

                'nombre': vendedor.nombre,

                'meta': meta,

                'venta': venta,

                'porcentaje': porcentaje

            })


            # Acumular únicamente las metas

            meta_empresa += meta


        # ==========================================
        # VENTA EMPRESA
        # VISITAS + LLAMADAS
        # ==========================================

        venta_empresa = venta_mes


        # ==========================================
        # CUMPLIMIENTO EMPRESA
        # ==========================================

        if meta_empresa > 0:

            cumplimiento_empresa = round(
                (venta_empresa / meta_empresa) * 100,
                1
            )

        else:

            cumplimiento_empresa = 0


    # ==========================================
    # VENDEDOR
    # ==========================================

    else:

        objetivo = Objetivo.query.filter(
            Objetivo.usuario_id == current_user.id,
            Objetivo.anio == ahora.year,
            Objetivo.mes == ahora.month
        ).first()


        meta_empresa = (
            objetivo.objetivo
            if objetivo
            else 0
        )


        venta_empresa = venta_mes


        if meta_empresa > 0:

            cumplimiento_empresa = round(
                (venta_empresa / meta_empresa) * 100,
                1
            )

        else:

            cumplimiento_empresa = 0


    # ==========================================
    # ENVIAR DATOS AL DASHBOARD
    # ==========================================

    return render_template(
        'dashboard.html',

        # ==========================================
        # KPI GENERALES
        # ==========================================

        clientes_total=clientes_total,

        clientes_con_venta=clientes_con_venta,

        visitas_total=visitas_total,

        visitas_mes=visitas_mes,

        prospectos_mes=prospectos_mes,

        llamadas_mes=llamadas_mes,

        # Venta total = Visitas + Llamadas
        venta_mes=venta_mes,

        # ==========================================
        # COMPATIBILIDAD CON EL HTML ACTUAL
        # ==========================================

        # Para la sección Objetivo Mensual del vendedor
        objetivo=meta_empresa,

        # Para "Venta Actual" y tarjeta Venta del Mes
        monto_mes=venta_mes,

        # Cumplimiento del vendedor o empresa
        cumplimiento=cumplimiento_empresa,

        # ==========================================
        # ADMIN / SUPERVISOR
        # ==========================================

        admin=admin,

        meta_empresa=meta_empresa,

        venta_empresa=venta_empresa,

        cumplimiento_empresa=cumplimiento_empresa,

        cumplimiento_vendedores=cumplimiento_vendedores
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
            <a href="/clientes">
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

        foto_fuera = (
            request.files.get('foto_fuera_camara')
            or
            request.files.get('foto_fuera_galeria')
        )

        foto_exhibidor = (
            request.files.get('foto_exhibidor_camara')
            or
            request.files.get('foto_exhibidor_galeria')
        )

        url_foto_fuera = None
        url_foto_exhibidor = None

        # =====================================
        # FOTO FUERA
        # =====================================

        if foto_fuera and foto_fuera.filename:

            resultado = cloudinary.uploader.upload(
                foto_fuera,
                folder="bitacora_visitas/fuera"
            )

            url_foto_fuera = resultado["secure_url"]

        # =====================================
        # FOTO EXHIBIDOR
        # =====================================

        if foto_exhibidor and foto_exhibidor.filename:

            resultado = cloudinary.uploader.upload(
                foto_exhibidor,
                folder="bitacora_visitas/exhibidor"
            )

            url_foto_exhibidor = resultado["secure_url"]



        proxima_visita = None


        if request.form.get('proxima_visita'):

            proxima_visita = datetime.strptime(
                request.form['proxima_visita'],
                '%Y-%m-%d'
            ).date()



        visita = Visita(
            cliente_id=request.form['cliente_id'],
            observaciones=request.form.get('observaciones'),
            venta_realizada='venta_realizada' in request.form,
            monto_venta=float(request.form.get('monto_venta') or 0),
            proxima_visita=proxima_visita,
            foto_fuera=url_foto_fuera,
            foto_exhibidor=url_foto_exhibidor,
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

    # =====================================================
    # VALIDAR PERMISOS
    # =====================================================

    # Los vendedores solamente pueden editar
    # sus propias visitas
    if (
        current_user.rol == 'vendedor'
        and visita.usuario_id != current_user.id
    ):
        return "Acceso denegado", 403


    # =====================================================
    # EDITAR VISITA
    # =====================================================

    if request.method == 'POST':

        # =================================================
        # OBSERVACIONES
        # =================================================

        visita.observaciones = request.form.get(
            'observaciones',
            ''
        )


        # =================================================
        # VENTA REALIZADA
        # =================================================

        visita.venta_realizada = (
            'venta_realizada' in request.form
        )


        # =================================================
        # MONTO DE VENTA
        # =================================================

        try:

            visita.monto_venta = float(
                request.form.get(
                    'monto_venta',
                    '0'
                ) or 0
            )

        except ValueError:

            visita.monto_venta = 0


        # =================================================
        # FOTO FUERA
        #
        # Aceptamos:
        # foto_fuera_camara
        # foto_fuera_galeria
        # foto_fuera
        # =================================================

        foto_fuera = (

            request.files.get(
                'foto_fuera_camara'
            )

            or

            request.files.get(
                'foto_fuera_galeria'
            )

            or

            request.files.get(
                'foto_fuera'
            )

        )


        if foto_fuera and foto_fuera.filename:

            try:

                resultado = cloudinary.uploader.upload(

                    foto_fuera,

                    folder="bitacora_visitas/fuera"

                )

                # Guardar URL de Cloudinary
                visita.foto_fuera = (
                    resultado["secure_url"]
                )

            except Exception as e:

                print(
                    "ERROR AL SUBIR FOTO FUERA:",
                    e
                )

                db.session.rollback()

                return (
                    "Error al subir la fotografía "
                    "de fuera del establecimiento."
                ), 500


        # =================================================
        # FOTO EXHIBIDOR
        #
        # Aceptamos:
        # foto_exhibidor_camara
        # foto_exhibidor_galeria
        # foto_exhibidor
        # =================================================

        foto_exhibidor = (

            request.files.get(
                'foto_exhibidor_camara'
            )

            or

            request.files.get(
                'foto_exhibidor_galeria'
            )

            or

            request.files.get(
                'foto_exhibidor'
            )

        )


        if foto_exhibidor and foto_exhibidor.filename:

            try:

                resultado = cloudinary.uploader.upload(

                    foto_exhibidor,

                    folder="bitacora_visitas/exhibidor"

                )

                # Guardar URL de Cloudinary
                visita.foto_exhibidor = (
                    resultado["secure_url"]
                )

            except Exception as e:

                print(
                    "ERROR AL SUBIR FOTO EXHIBIDOR:",
                    e
                )

                db.session.rollback()

                return (
                    "Error al subir la fotografía "
                    "del exhibidor."
                ), 500


        # =================================================
        # GUARDAR CAMBIOS EN POSTGRESQL
        # =================================================

        try:

            db.session.commit()

        except Exception as e:

            db.session.rollback()

            print(
                "ERROR AL GUARDAR VISITA:",
                e
            )

            return (
                "Error al guardar los cambios "
                "de la visita."
            ), 500


        # =================================================
        # REGRESAR AL HISTORIAL
        # =================================================

        return redirect(
            url_for('visitas')
        )


    # =====================================================
    # MOSTRAR FORMULARIO
    # =====================================================

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


    # =====================================================
    # VENTAS DE VISITAS
    # =====================================================

    consulta_visitas = db.session.query(

        Usuario.id.label('usuario_id'),

        Usuario.nombre.label('nombre'),

        # Cantidad de visitas que generaron venta
        func.count(Visita.id).label('ventas_visitas'),

        # Monto vendido mediante visitas
        func.coalesce(
            func.sum(Visita.monto_venta),
            0
        ).label('monto_visitas')

    ).outerjoin(

        Visita,
        Usuario.id == Visita.usuario_id

    ).filter(

        # SOLO VENDEDORES ACTIVOS
        Usuario.activo == True,

        Usuario.rol == 'vendedor',

        # SOLO VISITAS CON VENTA
        Visita.monto_venta > 0

    )


    # =====================================================
    # FILTRO FECHA INICIO
    # =====================================================

    if fecha_inicio:

        consulta_visitas = consulta_visitas.filter(

            db.func.date(Visita.fecha) >= fecha_inicio

        )


    # =====================================================
    # FILTRO FECHA FIN
    # =====================================================

    if fecha_fin:

        consulta_visitas = consulta_visitas.filter(

            db.func.date(Visita.fecha) <= fecha_fin

        )


    reporte_visitas = consulta_visitas.group_by(

        Usuario.id,

        Usuario.nombre

    ).all()


    # =====================================================
    # VENTAS DE LLAMADAS
    # =====================================================

    consulta_llamadas = db.session.query(

        Usuario.id.label('usuario_id'),

        # Cantidad de llamadas que generaron venta
        func.count(Llamada.id).label('ventas_llamadas'),

        # Monto vendido mediante llamadas
        func.coalesce(
            func.sum(Llamada.monto_venta),
            0
        ).label('monto_llamadas')

    ).outerjoin(

        Llamada,

        Usuario.id == Llamada.usuario_id

    ).filter(

        # SOLO VENDEDORES ACTIVOS
        Usuario.activo == True,

        Usuario.rol == 'vendedor',

        # SOLO LLAMADAS CON VENTA
        Llamada.monto_venta > 0

    )


    # =====================================================
    # FILTRO FECHA INICIO
    # =====================================================

    if fecha_inicio:

        consulta_llamadas = consulta_llamadas.filter(

            db.func.date(Llamada.fecha) >= fecha_inicio

        )


    # =====================================================
    # FILTRO FECHA FIN
    # =====================================================

    if fecha_fin:

        consulta_llamadas = consulta_llamadas.filter(

            db.func.date(Llamada.fecha) <= fecha_fin

        )


    reporte_llamadas = consulta_llamadas.group_by(

        Usuario.id

    ).all()


    # =====================================================
    # CONVERTIR LLAMADAS A DICCIONARIO
    # =====================================================

    llamadas_dict = {

        fila.usuario_id: {

            'ventas_llamadas':
                fila.ventas_llamadas or 0,

            'monto_llamadas':
                float(
                    fila.monto_llamadas or 0
                )

        }

        for fila in reporte_llamadas

    }


    # =====================================================
    # UNIFICAR VISITAS + LLAMADAS
    # =====================================================

    reporte = []


    for fila in reporte_visitas:

        datos_llamadas = llamadas_dict.get(

            fila.usuario_id,

            {
                'ventas_llamadas': 0,
                'monto_llamadas': 0
            }

        )


        # ---------------------------------------------
        # VENTAS
        # ---------------------------------------------

        ventas_visitas = (
            fila.ventas_visitas or 0
        )

        ventas_llamadas = (
            datos_llamadas['ventas_llamadas']
        )


        ventas = (

            ventas_visitas +

            ventas_llamadas

        )


        # ---------------------------------------------
        # MONTOS
        # ---------------------------------------------

        monto_visitas = float(

            fila.monto_visitas or 0

        )


        monto_llamadas = (

            datos_llamadas['monto_llamadas']

        )


        monto_total = (

            monto_visitas +

            monto_llamadas

        )


        # ---------------------------------------------
        # AGREGAR AL REPORTE
        # ---------------------------------------------

        reporte.append({

            'usuario_id':
                fila.usuario_id,

            'nombre':
                fila.nombre,

            'ventas_visitas':
                ventas_visitas,

            'ventas_llamadas':
                ventas_llamadas,

            'ventas':
                ventas,

            'monto_visitas':
                monto_visitas,

            'monto_llamadas':
                monto_llamadas,

            'monto':
                monto_total

        })


    # =====================================================
    # AGREGAR VENDEDORES QUE SOLO TIENEN VENTAS
    # POR LLAMADAS
    # =====================================================

    usuarios_reporte = {

        fila['usuario_id']

        for fila in reporte

    }


    for fila in reporte_llamadas:

        if fila.usuario_id not in usuarios_reporte:

            reporte.append({

                'usuario_id':
                    fila.usuario_id,

                'nombre':
                    Usuario.query.get(
                        fila.usuario_id
                    ).nombre,

                'ventas_visitas':
                    0,

                'ventas_llamadas':
                    fila.ventas_llamadas or 0,

                'ventas':
                    fila.ventas_llamadas or 0,

                'monto_visitas':
                    0,

                'monto_llamadas':
                    float(
                        fila.monto_llamadas or 0
                    ),

                'monto':
                    float(
                        fila.monto_llamadas or 0
                    )

            })


    # =====================================================
    # ORDENAR POR VENTA TOTAL
    # =====================================================

    reporte.sort(

        key=lambda x: x['monto'],

        reverse=True

    )


    # =====================================================
    # TOTALES
    # =====================================================

    total_ventas_visitas = sum(

        fila['ventas_visitas']

        for fila in reporte

    )


    total_ventas_llamadas = sum(

        fila['ventas_llamadas']

        for fila in reporte

    )


    total_ventas = sum(

        fila['ventas']

        for fila in reporte

    )


    total_monto_visitas = sum(

        fila['monto_visitas']

        for fila in reporte

    )


    total_monto_llamadas = sum(

        fila['monto_llamadas']

        for fila in reporte

    )


    total_general = sum(

        fila['monto']

        for fila in reporte

    )


    # =====================================================
    # MEJOR VENDEDOR
    # =====================================================

    mejor_vendedor = (

        reporte[0]

        if reporte

        else None

    )


    # =====================================================
    # DATOS PARA GRÁFICA
    # =====================================================

    labels = [

        fila['nombre']

        for fila in reporte

    ]


    montos = [

        fila['monto']

        for fila in reporte

    ]


    montos_visitas = [

        fila['monto_visitas']

        for fila in reporte

    ]


    montos_llamadas = [

        fila['monto_llamadas']

        for fila in reporte

    ]


    # =====================================================
    # RENDER
    # =====================================================

    return render_template(

        'reporte_ventas_vendedor.html',

        reporte=reporte,

        total_ventas_visitas=
            total_ventas_visitas,

        total_ventas_llamadas=
            total_ventas_llamadas,

        total_ventas=
            total_ventas,

        total_monto_visitas=
            total_monto_visitas,

        total_monto_llamadas=
            total_monto_llamadas,

        total_general=
            total_general,

        mejor_vendedor=
            mejor_vendedor,

        labels=
            labels,

        montos=
            montos,

        montos_visitas=
            montos_visitas,

        montos_llamadas=
            montos_llamadas

    )



@app.route('/reporte_visitas_vendedor')
@login_required
def reporte_visitas_vendedor():

    if current_user.rol not in ['admin', 'supervisor']:
        return "Acceso denegado"

    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')


    # =====================================================
    # VISITAS POR VENDEDOR
    # =====================================================

    consulta_visitas = db.session.query(
        Usuario.id.label('usuario_id'),
        Usuario.nombre.label('nombre'),
        func.count(Visita.id).label('visitas'),
        func.coalesce(
            func.sum(Visita.monto_venta),
            0
        ).label('venta_visitas')
    ).outerjoin(
        Visita,
        Usuario.id == Visita.usuario_id
    ).filter(
        Usuario.activo == True,
        Usuario.rol == 'vendedor'
    )

    if fecha_inicio:
        consulta_visitas = consulta_visitas.filter(
            db.func.date(Visita.fecha) >= fecha_inicio
        )

    if fecha_fin:
        consulta_visitas = consulta_visitas.filter(
            db.func.date(Visita.fecha) <= fecha_fin
        )

    reporte_visitas = consulta_visitas.group_by(
        Usuario.id,
        Usuario.nombre
    ).all()


    # =====================================================
    # LLAMADAS POR VENDEDOR
    # =====================================================

    consulta_llamadas = db.session.query(
        Usuario.id.label('usuario_id'),

        func.count(
            Llamada.id
        ).label('llamadas'),

        func.coalesce(
            func.sum(Llamada.monto_venta),
            0
        ).label('venta_llamadas')

    ).outerjoin(
        Llamada,
        Usuario.id == Llamada.usuario_id
    )

    if fecha_inicio:
        consulta_llamadas = consulta_llamadas.filter(
            db.func.date(Llamada.fecha) >= fecha_inicio
        )

    if fecha_fin:
        consulta_llamadas = consulta_llamadas.filter(
            db.func.date(Llamada.fecha) <= fecha_fin
        )

    reporte_llamadas = consulta_llamadas.group_by(
        Usuario.id
    ).all()


    # =====================================================
    # PROSPECTOS POR VENDEDOR
    # =====================================================

    consulta_prospectos = db.session.query(
        Usuario.id.label('usuario_id'),
        func.count(Prospecto.id).label('prospectos')
    ).outerjoin(
        Prospecto,
        Usuario.id == Prospecto.usuario_id
    ).filter(
        Usuario.activo == True,
        Usuario.rol == 'vendedor'
    )

    if fecha_inicio:
        consulta_prospectos = consulta_prospectos.filter(
            db.func.date(
                Prospecto.fecha_registro
            ) >= fecha_inicio
        )

    if fecha_fin:
        consulta_prospectos = consulta_prospectos.filter(
            db.func.date(
                Prospecto.fecha_registro
            ) <= fecha_fin
        )

    reporte_prospectos = consulta_prospectos.group_by(
        Usuario.id
    ).all()


    # =====================================================
    # CONVERTIR LLAMADAS A DICCIONARIO
    # =====================================================

    llamadas_dict = {

        fila.usuario_id: {

            'llamadas': fila.llamadas or 0,

            'venta_llamadas': float(
                fila.venta_llamadas or 0
            )

        }

        for fila in reporte_llamadas
    }


    # =====================================================
    # CONVERTIR PROSPECTOS A DICCIONARIO
    # =====================================================

    prospectos_dict = {

        fila.usuario_id: fila.prospectos or 0

        for fila in reporte_prospectos

    }


    # =====================================================
    # UNIR VISITAS + LLAMADAS + PROSPECTOS
    # =====================================================

    reporte = []

    for fila in reporte_visitas:

        # -----------------------------------------------
        # LLAMADAS
        # -----------------------------------------------

        datos_llamadas = llamadas_dict.get(

            fila.usuario_id,

            {
                'llamadas': 0,
                'venta_llamadas': 0
            }

        )


        # -----------------------------------------------
        # PROSPECTOS
        # -----------------------------------------------

        prospectos = prospectos_dict.get(
            fila.usuario_id,
            0
        )


        # -----------------------------------------------
        # VISITAS
        # -----------------------------------------------

        visitas = fila.visitas or 0


        # -----------------------------------------------
        # LLAMADAS
        # -----------------------------------------------

        llamadas = datos_llamadas['llamadas']


        # -----------------------------------------------
        # VENTAS
        # -----------------------------------------------

        venta_visitas = float(
            fila.venta_visitas or 0
        )

        venta_llamadas = float(
            datos_llamadas['venta_llamadas'] or 0
        )


        # -----------------------------------------------
        # ACTIVIDADES
        # -----------------------------------------------

        actividades = (
            visitas +
            llamadas +
            prospectos
        )


        # -----------------------------------------------
        # VENTA TOTAL
        # -----------------------------------------------

        venta_total = (
            venta_visitas +
            venta_llamadas
        )


        # -----------------------------------------------
        # AGREGAR AL REPORTE
        # -----------------------------------------------

        reporte.append({

            'usuario_id': fila.usuario_id,

            'nombre': fila.nombre,

            'visitas': visitas,

            'llamadas': llamadas,

            'prospectos': prospectos,

            'actividades': actividades,

            'venta_visitas': venta_visitas,

            'venta_llamadas': venta_llamadas,

            'venta_total': venta_total

        })


    # =====================================================
    # TOTALES GENERALES
    # =====================================================

    total_visitas = sum(
        fila['visitas']
        for fila in reporte
    )

    total_llamadas = sum(
        fila['llamadas']
        for fila in reporte
    )

    total_prospectos = sum(
        fila['prospectos']
        for fila in reporte
    )

    total_actividades = sum(
        fila['actividades']
        for fila in reporte
    )

    total_venta_visitas = sum(
        fila['venta_visitas']
        for fila in reporte
    )

    total_venta_llamadas = sum(
        fila['venta_llamadas']
        for fila in reporte
    )

    total_ventas = sum(
        fila['venta_total']
        for fila in reporte
    )


    # =====================================================
    # DATOS PARA GRÁFICAS
    # =====================================================

    labels = [
        fila['nombre']
        for fila in reporte
    ]

    visitas = [
        fila['visitas']
        for fila in reporte
    ]

    llamadas = [
        fila['llamadas']
        for fila in reporte
    ]

    prospectos = [
        fila['prospectos']
        for fila in reporte
    ]

    ventas = [
        fila['venta_total']
        for fila in reporte
    ]


    # =====================================================
    # RENDER
    # =====================================================

    return render_template(

        'reporte_visitas_vendedor.html',

        reporte=reporte,

        # Totales
        total_visitas=total_visitas,
        total_llamadas=total_llamadas,
        total_prospectos=total_prospectos,
        total_actividades=total_actividades,

        # Ventas
        total_venta_visitas=total_venta_visitas,
        total_venta_llamadas=total_venta_llamadas,
        total_ventas=total_ventas,

        # Gráficas
        labels=labels,
        visitas=visitas,
        llamadas=llamadas,
        prospectos=prospectos,
        ventas=ventas
    )


from datetime import date
@app.route('/reporte_proximas_visitas')
@login_required
def reporte_proximas_visitas():

    if current_user.rol not in ['admin', 'supervisor']:
        return "Acceso denegado"

    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')

    # =====================================================
    # FECHA ACTUAL
    # =====================================================

    hoy = date.today()

    # =====================================================
    # CONSULTA BASE
    # SOLO VENDEDORES ACTIVOS
    # =====================================================

    consulta = db.session.query(
        Visita
    ).join(
        Usuario,
        Usuario.id == Visita.usuario_id
    ).filter(

        # La visita debe tener fecha programada
        Visita.proxima_visita.isnot(None),

        # No mostrar visitas que ya pasaron
        Visita.proxima_visita >= hoy,

        # SOLO VENDEDORES ACTIVOS
        Usuario.activo == True,

        Usuario.rol == 'vendedor'

    )

    # =====================================================
    # FILTRO FECHA INICIO
    # =====================================================

    if fecha_inicio:

        consulta = consulta.filter(
            Visita.proxima_visita >= fecha_inicio
        )

    # =====================================================
    # FILTRO FECHA FIN
    # =====================================================

    if fecha_fin:

        consulta = consulta.filter(
            Visita.proxima_visita <= fecha_fin
        )

    # =====================================================
    # ORDENAR
    # =====================================================

    visitas = consulta.order_by(
        Visita.proxima_visita.asc()
    ).all()

    # =====================================================
    # INDICADORES
    # =====================================================

    total_visitas = len(visitas)

    # ---------------------------------------------
    # VISITAS PROGRAMADAS PARA HOY
    # ---------------------------------------------

    visitas_hoy = sum(

        1

        for visita in visitas

        if visita.proxima_visita == hoy

    )

    # ---------------------------------------------
    # VISITAS EN LOS PRÓXIMOS 7 DÍAS
    # ---------------------------------------------

    visitas_7_dias = sum(

        1

        for visita in visitas

        if visita.proxima_visita <= hoy + timedelta(days=7)

    )

    # =====================================================
    # RETORNAR
    # =====================================================

    return render_template(

        'reporte_proximas_visitas.html',

        visitas=visitas,

        total_visitas=total_visitas,

        visitas_hoy=visitas_hoy,

        visitas_7_dias=visitas_7_dias,

        hoy=hoy

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

            latitud=request.form.get('latitud'),

            longitud=request.form.get('longitud'),

            usuario_id=current_user.id

        )

        # Verificar objeto antes de guardar
        print("========== OBJETO ==========")
        print("Latitud:", prospecto.latitud)
        print("Longitud:", prospecto.longitud)
        print("============================")

        db.session.add(prospecto)
        db.session.commit()

        print("Prospecto guardado correctamente.")

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

@app.route('/llamadas')
@login_required
def llamadas():

    if current_user.rol in ['admin', 'supervisor']:

        llamadas = Llamada.query.order_by(
            Llamada.fecha.desc()
        ).all()

    else:

        llamadas = Llamada.query.filter_by(
            usuario_id=current_user.id
        ).order_by(
            Llamada.fecha.desc()
        ).all()

    return render_template(
        'llamadas.html',
        llamadas=llamadas
    )

@app.route(
    '/llamada/nueva',
    methods=['GET', 'POST']
)
@login_required
def nueva_llamada():

    clientes = Cliente.query.order_by(
        Cliente.nombre
    ).all()

    if request.method == 'POST':

        llamada = Llamada(

            cliente_id=request.form['cliente_id'],

            estatus=request.form['estatus'],

            monto_venta=float(
                request.form.get('monto_venta') or 0
            ),

            observaciones=request.form.get(
                'observaciones'
            ),

            usuario_id=current_user.id

        )

        db.session.add(llamada)

        db.session.commit()

        return redirect('/llamadas')

    return render_template(
        'nueva_llamada.html',
        clientes=clientes
    )

@app.route(
    '/llamada/editar/<int:id>',
    methods=['GET', 'POST']
)
@login_required
def editar_llamada(id):

    llamada = Llamada.query.get_or_404(id)

    # Los vendedores solamente pueden editar
    # sus propias llamadas
    if (
        current_user.rol == 'vendedor'
        and llamada.usuario_id != current_user.id
    ):
        return "Acceso denegado"

    if request.method == 'POST':

        llamada.estatus = request.form['estatus']

        llamada.monto_venta = float(
            request.form.get('monto_venta') or 0
        )

        llamada.observaciones = request.form.get(
            'observaciones'
        )

        db.session.commit()

        return redirect('/llamadas')

    return render_template(
        'editar_llamada.html',
        llamada=llamada
    )

@app.route('/llamada/eliminar/<int:id>')
@login_required
def eliminar_llamada(id):

    if current_user.rol != 'admin':
        return "Acceso denegado"

    llamada = Llamada.query.get_or_404(id)

    db.session.delete(llamada)

    db.session.commit()

    return redirect('/llamadas')

@app.route('/reporte_prospeccion')
@login_required
def reporte_prospeccion():

    if current_user.rol not in ['admin', 'supervisor']:
        return "Acceso denegado"

    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')

    # =====================================================
    # CONSULTA BASE
    # SOLO VENDEDORES ACTIVOS
    # =====================================================

    consulta = db.session.query(
        Prospecto
    ).join(
        Usuario,
        Usuario.id == Prospecto.usuario_id
    ).filter(
        Usuario.activo == True,
        Usuario.rol == 'vendedor'
    )

    # =====================================================
    # FILTRO FECHA INICIO
    # =====================================================

    if fecha_inicio:

        consulta = consulta.filter(
            db.func.date(
                Prospecto.fecha_registro
            ) >= fecha_inicio
        )

    # =====================================================
    # FILTRO FECHA FIN
    # =====================================================

    if fecha_fin:

        consulta = consulta.filter(
            db.func.date(
                Prospecto.fecha_registro
            ) <= fecha_fin
        )

    prospectos = consulta.order_by(
        Prospecto.fecha_registro.desc()
    ).all()

    # =====================================================
    # TOTAL DE PROSPECTOS
    # =====================================================

    total_prospectos = len(prospectos)

    # =====================================================
    # PROSPECTOS POR ESTATUS
    # =====================================================

    estatus_dict = {}

    for prospecto in prospectos:

        estatus = prospecto.estatus or 'Sin estatus'

        estatus_dict[estatus] = (
            estatus_dict.get(estatus, 0) + 1
        )

    labels_estatus = list(
        estatus_dict.keys()
    )

    prospectos_estatus = list(
        estatus_dict.values()
    )

    # =====================================================
    # PROSPECTOS POR VENDEDOR
    # =====================================================

    vendedores_dict = {}

    for prospecto in prospectos:

        if prospecto.usuario:

            nombre = prospecto.usuario.nombre

            vendedores_dict[nombre] = (
                vendedores_dict.get(nombre, 0) + 1
            )

    # Ordenar de mayor a menor
    vendedores_ordenados = sorted(
        vendedores_dict.items(),
        key=lambda x: x[1],
        reverse=True
    )

    labels_vendedores = [
        fila[0]
        for fila in vendedores_ordenados
    ]

    prospectos_vendedores = [
        fila[1]
        for fila in vendedores_ordenados
    ]

    # =====================================================
    # PROSPECTOS NUEVOS
    # =====================================================

    prospectos_nuevos = sum(
        1
        for prospecto in prospectos
        if (prospecto.estatus or '').lower() == 'nuevo'
    )

    # =====================================================
    # PORCENTAJE DE PROSPECTOS NUEVOS
    # =====================================================

    porcentaje_nuevos = (

        (prospectos_nuevos / total_prospectos) * 100

        if total_prospectos > 0

        else 0

    )

    # =====================================================
    # TABLA POR VENDEDOR
    # =====================================================

    reporte_vendedores = []

    for nombre, cantidad in vendedores_ordenados:

        porcentaje = (

            (cantidad / total_prospectos) * 100

            if total_prospectos > 0

            else 0

        )

        reporte_vendedores.append({

            'nombre': nombre,

            'prospectos': cantidad,

            'porcentaje': porcentaje

        })

    # =====================================================
    # RETORNAR
    # =====================================================

    return render_template(

        'reporte_prospeccion.html',

        prospectos=prospectos,

        total_prospectos=total_prospectos,

        prospectos_nuevos=prospectos_nuevos,

        porcentaje_nuevos=porcentaje_nuevos,

        labels_estatus=labels_estatus,

        prospectos_estatus=prospectos_estatus,

        labels_vendedores=labels_vendedores,

        prospectos_vendedores=prospectos_vendedores,

        reporte_vendedores=reporte_vendedores

    )




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
