import os
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
import matplotlib
matplotlib.use("Agg")  # Backend para servidores web
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

app = Flask(__name__)

# Configuración de la base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///empleos.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 1. Modelo de base de datos (coincide con las columnas de tu CSV)
class Empleo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_title = db.Column(db.String(100))
    experience_years = db.Column(db.Integer)
    education_level = db.Column(db.String(50))
    skills_count = db.Column(db.Integer)
    industry = db.Column(db.String(100))
    company_size = db.Column(db.String(50))
    location = db.Column(db.String(100))
    remote_work = db.Column(db.String(10))
    certifications = db.Column(db.Integer)
    salary = db.Column(db.Float)

# 2. Configuración de carpetas para los gráficos de Matplotlib
CHARTS_FOLDER = os.path.join('static', 'charts')
if not os.path.exists(CHARTS_FOLDER):
    os.makedirs(CHARTS_FOLDER)

# 3. Función para cargar el CSV a la base de Datos
def cargar_datos():
    with app.app_context():
        db.create_all()
        # Verificamos si la base ya tiene datos para no duplicar
        if not Empleo.query.first():
            # Construimos la ruta a la carpeta data/
            ruta_csv = os.path.join(os.path.dirname(__file__), 'data', 'job_salary_prediction_dataset.csv')
            
            if os.path.exists(ruta_csv):
                df = pd.read_csv(ruta_csv)
                # Cargamos los datos del DataFrame a la tabla 'empleo' de SQL
                df.to_sql('empleo', con=db.engine, if_exists='append', index=False)
                print("¡Base de datos cargada con éxito!")
            else:
                print(f"Error: No se encontró el archivo CSV en {ruta_csv}")

# --- IMPORTANTE: Se cargan los datos antes de que el servidor empiece a escuchar ---
cargar_datos()

# 4. Ruta Principal: Dashboard
@app.route('/')
def index():
    ruta_csv = os.path.join(os.path.dirname(__file__), 'data', 'job_salary_prediction_dataset.csv')
    df = pd.read_csv(ruta_csv)
    
    # 1. Agrupamos por industria y calculamos el promedio REAL de cada una
    # Usamos .reset_index() para que Pandas no se confunda
    data_grafico = df.groupby('industry')['salary'].mean().sort_values(ascending=True)

    # 2. Creamos el gráfico con un tamaño que le dé aire
    plt.figure(figsize=(10, 6))
    
    # Usamos colores variados (un degradado) para que se note la distinción
    colores = plt.cm.viridis(np.linspace(0, 1, len(data_grafico)))
    
    data_grafico.plot(kind='barh', color=colores)

    # 3. Ajustamos el eje X para que empiece un poco antes del mínimo 
    # Esto hace que las diferencias se vean más grandes
    # 1. Obtenemos el mínimo y el máximo de los promedios
    min_promedio = data_grafico.min()
    max_promedio = data_grafico.max()

    # 2. Ajustamos el zoom: 
    # Que empiece un 1% abajo del mínimo y termine un 1% arriba del máximo
    plt.xlim(min_promedio * 0.99, max_promedio * 1.01)

    plt.title('Diferencias Salariales por Industria', fontsize=14, pad=15)
    plt.xlabel('Salario Anual Promedio (USD)')
    plt.ylabel('Industria')
    plt.grid(axis='x', linestyle='--', alpha=0.3)
    
    plt.tight_layout()
    
    nombre_grafico = "salario_industria.png"
    plt.savefig(os.path.join(CHARTS_FOLDER, nombre_grafico))
    plt.close()

    total_empleos = len(df)
    promedio_gral = round(df['salary'].mean(), 2)

    return render_template('tp3.html', 
                           imagen=nombre_grafico, 
                           total=total_empleos, 
                           promedio=promedio_gral)

# 5. Ruta de Tabla con Buscador
@app.route('/tabla')
def tabla():
    busqueda = request.args.get('query', '')
    
    if busqueda:
        # Buscamos en la base de datos registros que contengan el texto
        resultados = Empleo.query.filter(Empleo.job_title.like(f'%{busqueda}%')).all()
    else:
        # Si no hay búsqueda, mostramos los primeros 100 para que cargue rápido
        resultados = Empleo.query.limit(100).all()
        
    return render_template('tabla.html', empleos=resultados, busqueda=busqueda)

@app.route('/simuladores', methods=['GET', 'POST'])
def simulador():
    df = pd.read_csv(os.path.join(os.path.dirname(__file__), 'data', 'job_salary_prediction_dataset.csv'))
    
    # Obtenemos las listas únicas para llenar los desplegables del formulario
    industrias = sorted(df['industry'].unique())
    puestos = sorted(df['job_title'].unique())
    educacion = sorted(df['education_level'].unique())
    tamanos = sorted(df['company_size'].unique())
    ubicaciones = sorted(df['location'].unique())

    resultado_simulado = None

    if request.method == 'POST':
        # Capturamos lo que el usuario eligió
        f_puesto = request.form.get('puesto')
        f_industria = request.form.get('industria')
        f_exp = request.form.get('experiencia')
        f_edu = request.form.get('educacion')
        f_tamano = request.form.get('tamano')
        f_loc = request.form.get('ubicacion')
        f_remoto = request.form.get('remoto')

        # Empezamos a filtrar el DataFrame
        query = df.copy()
        if f_puesto: query = query[query['job_title'] == f_puesto]
        if f_industria: query = query[query['industry'] == f_industria]
        if f_edu: query = query[query['education_level'] == f_edu]
        if f_tamano: query = query[query['company_size'] == f_tamano]
        if f_loc: query = query[query['location'] == f_loc]
        if f_remoto: query = query[query['remote_work'] == f_remoto]
        
        # Para la experiencia, buscamos valores cercanos (rango de +/- 2 años)
        if f_exp:
            exp_val = int(f_exp)
            query = query[(query['experience_years'] >= exp_val - 2) & (query['experience_years'] <= exp_val + 2)]

        # Calculamos el promedio de los resultados filtrados
        if not query.empty:
            resultado_simulado = round(query['salary'].mean(), 2)
        else:
            resultado_simulado = "No hay datos suficientes para esta combinación"

    return render_template('simulador.html', 
                           industrias=industrias, 
                           puestos=puestos, 
                           educacion=educacion,
                           tamanos=tamanos,
                           ubicaciones=ubicaciones,
                           resultado=resultado_simulado)

if __name__ == '__main__':
    # El cargar_datos() ya se ejecutó arriba, ahora iniciamos la app
    app.run(debug=True)