import os
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
import matplotlib
matplotlib.use("Agg")  # Backend para servidores
import matplotlib.pyplot as plt
import pandas as pd

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///empleos.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 1. Modelo de base de datos (actualizado para coincidir con el CSV)
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

# 2. Configuración de carpetas para gráficos
CHARTS_FOLDER = os.path.join('static', 'charts')
if not os.path.exists(CHARTS_FOLDER):
    os.makedirs(CHARTS_FOLDER)

def cargar_datos():
    with app.app_context():
        db.create_all()
        if not Empleo.query.first():
            # Leemos el CSV y lo pasamos a la base de datos
            df = pd.read_csv('data/job_salary_prediction_dataset.csv')
            df.to_sql('empleo', con=db.engine, if_exists='append', index=False)


# 3. Ruta Principal: Dashboard con Gráficos
@app.route('/')
def index():
    # Usamos pandas para procesar datos rápido para el gráfico
    df = pd.read_csv('data/job_salary_prediction_dataset.csv')
    
    # Gráfico 1: Salario promedio por Industria
    plt.figure(figsize=(10, 5))
    df.groupby('industry')['salary'].mean().sort_values().plot(kind='barh', color='skyblue')
    plt.title('Salario Promedio por Industria')
    plt.xlabel('Salario Anual')
    plt.tight_layout()
    
    nombre_grafico = "salario_industria.png"
    plt.savefig(os.path.join(CHARTS_FOLDER, nombre_grafico))
    plt.close()

    # Datos rápidos para las "Cards" de Bootstrap
    total_empleos = len(df)
    promedio_gral = round(df['salary'].mean(), 2)

    return render_template('tp3.html', 
                           imagen=nombre_grafico, 
                           total=total_empleos, 
                           promedio=promedio_gral)

# 4. Ruta de Tabla con Buscador
@app.route('/tabla')
def tabla():
    # Obtenemos el término de búsqueda del formulario (si existe)
    busqueda = request.args.get('query', '')
    
    if busqueda:
        # Filtramos en la base de datos por título de trabajo
        resultados = Empleo.query.filter(Empleo.job_title.like(f'%{busqueda}%')).all()
    else:
        # Si no hay búsqueda, mostramos los primeros 50
        resultados = Empleo.query.limit(50).all()
        
    return render_template('tabla.html', empleos=resultados, busqueda=busqueda)

if __name__ == '__main__':
    app.run(debug=True)
    cargar_datos()