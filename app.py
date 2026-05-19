import os
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
import matplotlib
matplotlib.use("Agg")  # Backend para servidores web
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import plotly.express as px

app = Flask(__name__)

# Configuración de la base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///empleos.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 1. Modelo de base de datos
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

# 2. Configuración de carpetas para gráficos estáticos
CHARTS_FOLDER = os.path.join('static', 'charts')
if not os.path.exists(CHARTS_FOLDER):
    os.makedirs(CHARTS_FOLDER)

# 3. Función para cargar el CSV a la base de Datos
def cargar_datos():
    with app.app_context():
        db.create_all()
        if not Empleo.query.first():
            ruta_csv = os.path.join(os.path.dirname(__file__), 'data', 'job_salary_prediction_dataset.csv')
            if os.path.exists(ruta_csv):
                df = pd.read_csv(ruta_csv)
                df.to_sql('empleo', con=db.engine, if_exists='append', index=False)
                print("¡Base de datos cargada con éxito!")
            else:
                print(f"Error: No se encontró el archivo CSV en {ruta_csv}")

cargar_datos()

# 4. Ruta Principal: Dashboard (Matplotlib)
@app.route('/')
def index():
    ruta_csv = os.path.join(os.path.dirname(__file__), 'data', 'job_salary_prediction_dataset.csv')
    df = pd.read_csv(ruta_csv)
    
    data_grafico = df.groupby('industry')['salary'].mean().sort_values(ascending=True)
    plt.figure(figsize=(10, 6))
    colores = plt.cm.viridis(np.linspace(0, 1, len(data_grafico)))
    data_grafico.plot(kind='barh', color=colores)

    min_promedio = data_grafico.min()
    max_promedio = data_grafico.max()
    plt.xlim(min_promedio * 0.99, max_promedio * 1.01)

    plt.title('Diferencias Salariales por Industria', fontsize=14, pad=15)
    plt.xlabel('Salario Anual Promedio (USD)')
    plt.ylabel('Industria')
    plt.grid(axis='x', linestyle='--', alpha=0.3)
    
    plt.tight_layout()
    nombre_grafico = "salario_industria.png"
    plt.savefig(os.path.join(CHARTS_FOLDER, nombre_grafico))
    plt.close()   

    return render_template('tp3.html', 
                           imagen=nombre_grafico, 
                           total=len(df), 
                           promedio=round(df['salary'].mean(), 2))

# 5. Ruta de Tabla y Gráfico Interactivo (Plotly)
@app.route('/tabla', methods=['GET', 'POST'])
def tabla():
    # Obtener el puesto seleccionado del dropdown
    busqueda = request.args.get('query', '')
    
    ruta_csv = os.path.join(os.path.dirname(__file__), 'data', 'job_salary_prediction_dataset.csv')
    df2 = pd.read_csv(ruta_csv)
    
    # Lista de puestos únicos para el selector del template
    lista_puestos = sorted(df2['job_title'].unique())

    if busqueda:
        # Filtrado exacto para el gráfico de Plotly
        df_filtrado = df2[df2['job_title'] == busqueda]
        # Filtrado exacto en la base de datos ordenado por experiencia
        resultados = Empleo.query.filter_by(job_title=busqueda)\
                          .order_by(Empleo.experience_years.asc()).all()
    else:
        df_filtrado = df2
        # Si no hay búsqueda, mostramos los primeros 100 registros generales
        resultados = Empleo.query.order_by(Empleo.experience_years.asc()).limit(100).all()
    
    # Creación del Boxplot
    fig = px.box(
        df_filtrado, 
        x="experience_years", 
        y="salary", 
        color="education_level",
        points=False, 
        notched=True, 
        labels={
            "experience_years": "Años de Experiencia",
            "salary": "Salario Anual (USD)"
        }
    )

    #Etiquetas en español y formato moneda ($)
    fig.update_traces(
        hovertemplate="""
        <b>%{x} Años de Exp.</b><br><br>
        Máximo: %{max:$,.0f}<br>
        Prom. Máximo (Q3): %{q3:$,.0f}<br>
        Mediana: %{median:$,.0f}<br>
        Prom. Mínimo (Q1): %{q1:$,.0f}<br>
        Mínimo: %{min:$,.0f}
        <extra></extra>
        """
    )

    fig.update_layout(showlegend=True, legend_title_text="Niveles de Educación")
    fig.for_each_trace(lambda t: t.update(visible=True if t.name == "Bachelor" else "legendonly"))
    
    graph_html = fig.to_html(full_html=False)

    return render_template('tabla.html',
                           empleos=resultados,
                           puestos=lista_puestos, # Nueva variable para el select
                           busqueda=busqueda,
                           plot_div=graph_html)

# Simulador de Salarios
@app.route('/simuladores', methods=['GET', 'POST'])
def simulador():
    ruta_csv = os.path.join(os.path.dirname(__file__), 'data', 'job_salary_prediction_dataset.csv')
    df = pd.read_csv(ruta_csv)
    
    cantidad = 0
    resultado_simulado = None
    seleccion = {} 

    if request.method == 'POST':
        seleccion = {
            'puesto': request.form.get('puesto'),
            'industria': request.form.get('industria'),
            'experiencia': request.form.get('experiencia'),
            'educacion': request.form.get('educacion'),
            'tamano': request.form.get('tamano'),
            'ubicacion': request.form.get('ubicacion'),
            'remoto': request.form.get('remoto')
        }

        query = df.copy()
        if seleccion['puesto']: query = query[query['job_title'] == seleccion['puesto']]
        if seleccion['industria']: query = query[query['industry'] == seleccion['industria']]
        if seleccion['educacion']: query = query[query['education_level'] == seleccion['educacion']]
        if seleccion['tamano']: query = query[query['company_size'] == seleccion['tamano']]
        if seleccion['ubicacion']: query = query[query['location'] == seleccion['ubicacion']]
        if seleccion['remoto']: query = query[query['remote_work'] == seleccion['remoto']]
        
        if seleccion['experiencia']:
            exp_val = int(seleccion['experiencia'])
            query = query[(query['experience_years'] >= exp_val - 2) & (query['experience_years'] <= exp_val + 2)]
        
        cantidad = len(query)
        resultado_simulado = round(query['salary'].mean(), 2) if not query.empty else "Sin datos"

    return render_template('simulador.html', 
                           industrias=sorted(df['industry'].unique()), 
                           puestos=sorted(df['job_title'].unique()), 
                           educacion=sorted(df['education_level'].unique()),
                           tamanos=sorted(df['company_size'].unique()),
                           ubicaciones=sorted(df['location'].unique()),
                           resultado=resultado_simulado,
                           cantidad_coincidencias=cantidad,
                           seleccion=seleccion) 

if __name__ == '__main__':
    app.run(debug=True)