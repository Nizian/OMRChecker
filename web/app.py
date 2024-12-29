import glob
import os
import json
import pandas as pd
from flask import Flask, render_template, request, send_file, redirect, url_for
import subprocess
import fitz  # PyMuPDF para manejar PDFs
import shutil  # Para copiar archivos
import datetime  # Cambiamos la forma de importar

# Define rutas absolutas
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'web', 'uploads')
RESULT_FOLDER = os.path.join(BASE_DIR, 'web', 'results')

# Crear carpetas necesarias
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

app = Flask(__name__)

# Agregar os.path.exists como variable global para las plantillas
@app.context_processor
def utility_processor():
    return dict(os=os, UPLOAD_FOLDER=UPLOAD_FOLDER)

# Agregar el filtro personalizado para formatear fechas
@app.template_filter('datetime')
def format_datetime(value):
    dt = datetime.datetime.fromisoformat(value)
    return dt.strftime('%d/%m/%Y %H:%M')

def get_evaluations():
    """Devuelve la lista de evaluaciones disponibles ordenadas por fecha de creación."""
    evaluations = []
    for d in os.listdir(UPLOAD_FOLDER):
        eval_path = os.path.join(UPLOAD_FOLDER, d)
        if os.path.isdir(eval_path):
            info_path = os.path.join(eval_path, 'info.json')
            if os.path.exists(info_path):
                with open(info_path, 'r') as f:
                    info = json.load(f)
                    evaluations.append(info)
    
    # Ordenar por fecha de creación (más reciente primero)
    evaluations.sort(key=lambda x: x['created_at'], reverse=True)
    return evaluations

@app.route('/')
def index():
    evaluations = get_evaluations()
    current_evaluation = request.args.get('evaluation', evaluations[0]['name'] if evaluations else None)
    
    current_answers = None
    if current_evaluation:
        answers_file = os.path.join(UPLOAD_FOLDER, current_evaluation, 'answers.json')
        if os.path.exists(answers_file):
            with open(answers_file, 'r') as f:
                current_answers = json.load(f)
    
    return render_template('index.html', 
                         evaluations=evaluations, 
                         current_evaluation=current_evaluation, 
                         current_answers=current_answers)

@app.route('/create_evaluation', methods=['GET', 'POST'])
def create_evaluation():
    if request.method == 'POST':
        evaluation_name = request.form.get("evaluationName").strip()
        if not evaluation_name:
            return "Nombre de la evaluación no válido.", 400
        
        evaluation_path = os.path.join(UPLOAD_FOLDER, evaluation_name)
        sheet_templates_path = os.path.join(BASE_DIR, 'sheet_templates', 'template.json')
        
        if not os.path.exists(evaluation_path):
            os.makedirs(evaluation_path)
            
            # Copiar el template.json
            if os.path.exists(sheet_templates_path):
                shutil.copy(sheet_templates_path, os.path.join(evaluation_path, 'template.json'))
            else:
                return "No se encontró el archivo template.json en la carpeta sheet_templates.", 400

            # Guardar información de la evaluación
            eval_info = {
                'name': evaluation_name,
                'created_at': datetime.datetime.now().isoformat()
            }
            with open(os.path.join(evaluation_path, 'info.json'), 'w') as f:
                json.dump(eval_info, f)
            
            return redirect(url_for('index', evaluation=evaluation_name))
        else:
            return "La evaluación ya existe.", 400
    
    return render_template('create_evaluation.html')

@app.route('/set_template', methods=['GET', 'POST'])
def set_template():
    current_evaluation = request.args.get('evaluation')
    if not current_evaluation:
        return redirect(url_for('index'))
    
    evaluation_path = os.path.join(UPLOAD_FOLDER, current_evaluation)
    answers_file = os.path.join(evaluation_path, 'answers.json')

    if request.method == 'POST':
        num_questions = int(request.form.get("numQuestions"))
        correct_answers = {
            f"q{i}": request.form.get(f"q{i}") for i in range(1, num_questions + 1)
        }

        with open(answers_file, 'w') as f:
            json.dump(correct_answers, f, indent=4)

        return redirect(url_for('index', evaluation=current_evaluation))
    
    current_answers = None
    if os.path.exists(answers_file):
        with open(answers_file, 'r') as f:
            current_answers = json.load(f)
    
    return render_template('set_template.html', current_answers=current_answers, evaluation=current_evaluation)

def save_evaluations(evaluations):
    """Guarda la lista de evaluaciones en sus respectivos archivos info.json."""
    for eval_info in evaluations:
        eval_path = os.path.join(UPLOAD_FOLDER, eval_info['name'])
        info_path = os.path.join(eval_path, 'info.json')
        with open(info_path, 'w') as f:
            json.dump(eval_info, f)

@app.route('/delete_evaluation', methods=['POST'])
def delete_evaluation():
    evaluation_name = request.form['evaluation_name']
    # 1. Eliminar la evaluación de la lista de evaluaciones
    evaluations = get_evaluations()
    evaluations = [ev for ev in evaluations if ev['name'] != evaluation_name]
    save_evaluations(evaluations)

    # 2.  Eliminar los archivos asociados a la evaluación
    evaluation_path = os.path.join(UPLOAD_FOLDER, evaluation_name)
    if os.path.exists(evaluation_path):
        try:
            # Eliminar la carpeta de la evaluación y su contenido
            shutil.rmtree(evaluation_path) 
        except OSError as e:
            print(f"Error al eliminar la carpeta: {e}")
            # Puedes manejar el error de alguna manera, 
            # como mostrar un mensaje al usuario

    return redirect('/')

@app.route('/upload', methods=['POST'])
def upload():
    # Obtener la evaluación seleccionada del formulario
    current_evaluation = request.form.get("evaluation")
    if not current_evaluation:
        return "Debes seleccionar una evaluación.", 400

    # Rutas de la evaluación actual
    evaluation_path = os.path.join(UPLOAD_FOLDER, current_evaluation)
    template_file = os.path.join(evaluation_path, 'template.json')
    answers_file = os.path.join(evaluation_path, 'answers.json')
    upload_dir = os.path.join(evaluation_path, 'images')
    results_dir = os.path.join(evaluation_path, 'results')
    os.makedirs(upload_dir, exist_ok=True)

    # Limpiar el directorio de resultados antes del procesamiento
    if os.path.exists(results_dir):
        shutil.rmtree(results_dir)
    os.makedirs(results_dir, exist_ok=True)

    # Validar que el archivo template.json exista en la evaluación seleccionada
    if not os.path.exists(template_file):
        return f"El archivo template.json no se encuentra en la evaluación '{current_evaluation}'. Por favor, configúralo correctamente.", 400

    # Validar que el archivo answers.json exista en la evaluación seleccionada
    if not os.path.exists(answers_file):
        return f"El archivo answers.json no se encuentra en la evaluación '{current_evaluation}'. Por favor, configúralo correctamente.", 400

    try:
        # Verificar que se haya subido un archivo
        if 'file' not in request.files:
            return "No file uploaded", 400

        # Guardar el archivo subido
        file = request.files['file']
        filepath = os.path.join(upload_dir, file.filename)
        file.save(filepath)

        # Si el archivo es un PDF, convertirlo en imágenes
        if filepath.lower().endswith('.pdf'):
            pdf_dir = os.path.join(upload_dir, 'pdf_pages')

            # Limpiar el directorio para evitar archivos residuales
            if os.path.exists(pdf_dir):
                shutil.rmtree(pdf_dir)
            os.makedirs(pdf_dir)

            # Convertir PDF a imágenes
            pdf_doc = fitz.open(filepath)
            for page_num in range(len(pdf_doc)):
                page = pdf_doc.load_page(page_num)
                pix = page.get_pixmap()
                image_path = os.path.join(pdf_dir, f'page_{page_num + 1}.png')
                pix.save(image_path)
            pdf_doc.close()

            # Usar las imágenes generadas
            image_files = [os.path.join(pdf_dir, f) for f in os.listdir(pdf_dir) if f.endswith('.png')]
            image_files.sort()  # Asegurar orden correcto de las páginas
        else:
            # Procesar como una única imagen
            image_files = [filepath]

        # Leer respuestas correctas
        with open(answers_file, 'r') as f:
            correct_answers = json.load(f)
        num_questions_defined = len(correct_answers)

        # Procesar cada imagen individualmente
        all_results = []
        temp_dir = os.path.join(upload_dir, 'temp_processing')


        for index, img_file in enumerate(image_files):
            # Crear directorio temporal limpio
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            os.makedirs(temp_dir)
            
            # Copiar la imagen actual y el template al directorio temporal
            temp_image_path = os.path.join(temp_dir, os.path.basename(img_file))
            shutil.copy(img_file, temp_image_path)
            shutil.copy(template_file, os.path.join(temp_dir, 'template.json'))
            
            # Limpiar directorio de resultados
            results_csv_dir = os.path.join(results_dir, "Results")
            if os.path.exists(results_csv_dir):
                shutil.rmtree(results_csv_dir)
            os.makedirs(results_csv_dir)

            # Ejecutar main.py solo para la imagen actual
            command = [
                "python3", os.path.abspath(os.path.join(BASE_DIR, "main.py")),
                "--inputDir", temp_dir,
                "--outputDir", os.path.abspath(results_dir)
            ]
            subprocess.run(command, check=True, capture_output=True, text=True)

            # Buscar el archivo CSV generado
            result_files = glob.glob(os.path.join(results_dir, "Results", "Results_*.csv"))
            if not result_files:
                raise FileNotFoundError(f"No se encontró ningún archivo CSV para la página {index + 1}")
            
            # Leer el CSV y agregar información de la página
            data = pd.read_csv(result_files[0])
            if len(image_files) > 1:
                data['file_id'] = os.path.basename(img_file) + f" (Página {index + 1})"
            
            all_results.append(data)

        # Limpiar directorio temporal al finalizar
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

        # Combinar resultados de todas las páginas
        combined_results = pd.concat(all_results, ignore_index=True)

        # Calcular respuestas correctas e incorrectas
        combined_results['correct'] = [
            sum(
                row[f"q{i+1}"] == correct_answers[f"q{i+1}"]
                for i in range(num_questions_defined)
            )
            for _, row in combined_results.iterrows()
        ]
        combined_results['incorrect'] = num_questions_defined - combined_results['correct']

        # Crear resumen con las columnas de preguntas dinámicas
        columns = ['file_id', 'correct', 'incorrect'] + [f"q{i+1}" for i in range(num_questions_defined)]
        summary = combined_results[columns]
        summary.rename(columns={
            'file_id': 'Nombre',
            'correct': 'Respuestas correctas',
            'incorrect': 'Respuestas incorrectas'
        }, inplace=True)
        summary['Cantidad total'] = num_questions_defined

        # Generar un archivo Excel en la carpeta de la evaluación
        excel_output_file = os.path.join(results_dir, f"{current_evaluation}_results.xlsx")
        summary.to_excel(excel_output_file, index=False, sheet_name="Resultados")

        # Convertir a HTML para mostrar en la plantilla
        summary_html = summary.to_html(classes='table table-bordered', index=False)

        # Guardar una copia del resumen en formato JSON para acceso posterior
        summary_dict = summary.to_dict('records')
        results_json_file = os.path.join(results_dir, f"{current_evaluation}_results.json")
        with open(results_json_file, 'w') as f:
            json.dump({
                'summary': summary_dict,
                'processed_at': datetime.datetime.now().isoformat(),
                'total_students': len(summary_dict),
                'total_questions': num_questions_defined,
                'total_correct': summary['Respuestas correctas'].mean(),
                'total_incorrect': summary['Respuestas incorrectas'].mean()
            }, f)

        return render_template(
            'results.html',
            table=summary_html,
            excel_file=os.path.basename(excel_output_file),
            current_evaluation=current_evaluation
        )

        for index, img_file in enumerate(image_files):
            # Crear directorio temporal limpio
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            os.makedirs(temp_dir)
            
            # Copiar la imagen actual y el template al directorio temporal
            temp_image_path = os.path.join(temp_dir, os.path.basename(img_file))
            shutil.copy(img_file, temp_image_path)
            shutil.copy(template_file, os.path.join(temp_dir, 'template.json'))
            
            # Limpiar directorio de resultados
            results_csv_dir = os.path.join(results_dir, "Results")
            if os.path.exists(results_csv_dir):
                shutil.rmtree(results_csv_dir)
            os.makedirs(results_csv_dir)

            # Ejecutar main.py solo para la imagen actual
            command = [
                "python3", os.path.abspath(os.path.join(BASE_DIR, "main.py")),
                "--inputDir", temp_dir,
                "--outputDir", os.path.abspath(results_dir)
            ]
            subprocess.run(command, check=True, capture_output=True, text=True)

            # Buscar el archivo CSV generado
            result_files = glob.glob(os.path.join(results_dir, "Results", "Results_*.csv"))
            if not result_files:
                raise FileNotFoundError(f"No se encontró ningún archivo CSV para la página {index + 1}")
            
            # Leer el CSV y agregar información de la página
            data = pd.read_csv(result_files[0])
            if len(image_files) > 1:
                data['file_id'] = os.path.basename(img_file) + f" (Página {index + 1})"
            
            all_results.append(data)

        # Limpiar directorio temporal al finalizar
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

        # Combinar resultados de todas las páginas
        combined_results = pd.concat(all_results, ignore_index=True)

        # Calcular respuestas correctas e incorrectas
        combined_results['correct'] = [
            sum(
                row[f"q{i+1}"] == correct_answers[f"q{i+1}"]
                for i in range(num_questions_defined)
            )
            for _, row in combined_results.iterrows()
        ]
        combined_results['incorrect'] = num_questions_defined - combined_results['correct']

        # Crear resumen con las columnas de preguntas dinámicas
        columns = ['file_id', 'correct', 'incorrect'] + [f"q{i+1}" for i in range(num_questions_defined)]
        summary = combined_results[columns]
        summary.rename(columns={
            'file_id': 'Nombre',
            'correct': 'Respuestas correctas',
            'incorrect': 'Respuestas incorrectas'
        }, inplace=True)
        summary['Cantidad total'] = num_questions_defined

        

        # Generar un archivo Excel en la carpeta de la evaluación
        excel_output_file = os.path.join(results_dir, f"{current_evaluation}_results.xlsx")
        summary.to_excel(excel_output_file, index=False, sheet_name="Resultados")

        # Convertir a HTML para mostrar en la plantilla
        summary_html = summary.to_html(classes='table table-bordered', index=False)

        # Mostrar la tabla en una nueva página junto con la opción de descarga
        return render_template(
            'results.html',
            table=summary_html,
            excel_file=os.path.basename(excel_output_file),
            current_evaluation=current_evaluation
        )

    except subprocess.CalledProcessError as e:
        return f"Error en el procesamiento: {e.stderr or e.output}", 500
    except FileNotFoundError as e:
        return str(e), 500
    except Exception as e:
        return f"Error inesperado: {str(e)}", 500
    
@app.route('/view_results/<evaluation>')
def view_results(evaluation):
    results_dir = os.path.join(UPLOAD_FOLDER, evaluation, 'results')
    results_json_file = os.path.join(results_dir, f"{evaluation}_results.json")
    excel_file = f"{evaluation}_results.xlsx"
    
    if not os.path.exists(results_json_file):
        return "No hay resultados disponibles para esta evaluación.", 404
        
    with open(results_json_file, 'r') as f:
        results_data = json.load(f)
        
    # Convertir los datos del resumen a DataFrame y luego a HTML
    summary_df = pd.DataFrame(results_data['summary'])
    summary_html = summary_df.to_html(classes='table table-bordered', index=False)
    
    return render_template(
        'results.html',
        table=summary_html,
        excel_file=excel_file,
        current_evaluation=evaluation,
        processed_at=results_data['processed_at']
    )


@app.route('/web/results/<evaluation>/<path:filename>')
def download_file(evaluation, filename):
    # Ruta de la carpeta results de la evaluación seleccionada
    file_path = os.path.join(UPLOAD_FOLDER, evaluation, 'results', filename)
    if not os.path.exists(file_path):
        return f"El archivo {filename} no se encuentra disponible.", 404
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
