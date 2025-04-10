from flask import Flask, render_template, request, send_file, redirect, url_for
import os
import pandas as pd
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DOWNLOAD_FOLDER'] = 'downloads'
app.config['ALLOWED_EXTENSIONS'] = {'xlsx', 'xls', 'csv'}

# Criar diretórios necessários se não existirem
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload_prospec', methods=['POST'])
def upload_prospec():
    if 'file' not in request.files:
        return redirect(request.url)
    
    file = request.files['file']
    
    if file.filename == '':
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Aqui você pode adicionar sua lógica para processar o arquivo
        # Por exemplo: processar_prospec(filepath)
        
        return redirect(url_for('index'))
    
    return redirect(url_for('index'))

@app.route('/download_matches')
def download_matches():
    # Lógica para gerar o arquivo de matches
    # Se o arquivo já existir:
    # return send_file(os.path.join(app.config['DOWNLOAD_FOLDER'], 'matches.xlsx'))
    
    # Temporário, apenas para exemplo
    return redirect(url_for('index'))

@app.route('/upload_validated', methods=['POST'])
def upload_validated():
    if 'file' not in request.files:
        return redirect(request.url)
    
    file = request.files['file']
    
    if file.filename == '':
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Aqui você pode adicionar sua lógica para processar o arquivo validado
        # Por exemplo: processar_validado(filepath)
        
        return redirect(url_for('index'))
    
    return redirect(url_for('index'))

@app.route('/download_final_matches')
def download_final_matches():
    # Lógica para gerar o arquivo final de matches
    # Se o arquivo já existir:
    # return send_file(os.path.join(app.config['DOWNLOAD_FOLDER'], 'final_matches.xlsx'))
    
    # Temporário, apenas para exemplo
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)