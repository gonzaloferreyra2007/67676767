import os
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
import matplotlib
matplotlib.use("Agg")  # Backend para servidores web
import matplotlib.pyplot as plt
import pandas as pd

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
    
    # Creamos el gráfico de Salario promedio por Industria
    plt.figure(figsize=(10, 5))
    df.groupby('industry')['salary'].mean().sort_values().plot(kind='barh', color='skyblue')
    plt.title('Salario Promedio por Industria')
    plt.xlabel('Salario Anual')
    plt.tight_layout()
    
    nombre_grafico = "salario_industria.png"
    plt.savefig(os.path.join(CHARTS_FOLDER, nombre_grafico))
    plt.close()

    # Datos para las tarjetas de Bootstrap
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

if __name__ == '__main__':
    # El cargar_datos() ya se ejecutó arriba, ahora iniciamos la app
    app.run(debug=True)