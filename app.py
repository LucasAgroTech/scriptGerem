from flask import Flask, render_template, request, send_file, redirect, url_for, session, flash
import os
import pandas as pd
import numpy as np
from werkzeug.utils import secure_filename
import uuid
from pathlib import Path
import sys
import datetime
from dotenv import load_dotenv

# Adicionar diretório raiz ao sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Importar módulos do SharePoint
from office365_api.sharepoint_client import SharePointClient

app = Flask(__name__)
app.secret_key = 'chave-secreta-para-desenvolvimento'  # Substitua por uma chave segura em produção
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DOWNLOAD_FOLDER'] = 'downloads'
app.config['ALLOWED_EXTENSIONS'] = {'xlsx', 'xls', 'csv'}
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = 28800  # 8 horas

# Criar diretórios necessários se não existirem
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)

# Definições do SharePoint
SHAREPOINT_SITE = 'https://embrapii.sharepoint.com/sites/GEPES'
SHAREPOINT_FILE_PATH = 'General/Lucas Pinheiro/scriptGerem/prospec_consolidado.xlsx'

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_sharepoint_client():
    """Cria um cliente SharePoint com as credenciais da sessão"""
    if 'sharepoint_email' not in session or 'sharepoint_password' not in session:
        return None
    
    try:
        return SharePointClient(
            SHAREPOINT_SITE,
            session['sharepoint_email'],
            session['sharepoint_password']
        )
    except Exception as e:
        print(f"Erro ao criar cliente SharePoint: {str(e)}")
        return None

@app.route('/')
def index():
    """Rota principal, verifica se o usuário está logado"""
    if 'sharepoint_email' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login e processamento do formulário de login"""
    error = None
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # Validar credenciais no SharePoint
        try:
            # Tentar criar um cliente SharePoint para validar as credenciais
            sp_client = SharePointClient(SHAREPOINT_SITE, email, password)
            
            # Se não levantar erro, as credenciais são válidas
            session['sharepoint_email'] = email
            session['sharepoint_password'] = password
            session.permanent = True
            
            # Redirecionar para a página principal
            return redirect(url_for('index'))
            
        except Exception as e:
            error = f"Falha na autenticação. Verifique suas credenciais."
            print(f"Erro de login: {str(e)}")
    
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    """Encerra a sessão do usuário"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/upload_prospec', methods=['POST'])
def upload_prospec():
    """Processa o upload de uma planilha Prospec Gerem"""
    # Verificar se o usuário está logado
    if 'sharepoint_email' not in session:
        return redirect(url_for('login'))
    
    if 'file' not in request.files:
        flash('Nenhum arquivo selecionado')
        return redirect(url_for('index'))
    
    file = request.files['file']
    
    if file.filename == '':
        flash('Nenhum arquivo selecionado')
        return redirect(url_for('index'))
    
    if file and allowed_file(file.filename):
        # Salvar o arquivo localmente
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Processar a planilha
        try:
            # Obter cliente SharePoint
            sp_client = get_sharepoint_client()
            if not sp_client:
                flash('Erro de conexão com o SharePoint')
                return redirect(url_for('index'))
            
            # Ler o arquivo local
            if filepath.endswith('.csv'):
                df_new = pd.read_csv(filepath, encoding='utf-8-sig')
            else:
                df_new = pd.read_excel(filepath)
            
            # Verificar se as colunas necessárias existem
            required_columns = ["id", "data", "empresa"]
            missing_columns = [col for col in required_columns if col not in df_new.columns]
            
            if missing_columns:
                flash(f"Colunas obrigatórias ausentes: {', '.join(missing_columns)}")
                return redirect(url_for('index'))
            
            # Adicionar colunas se não existirem
            if "nome_capital" not in df_new.columns:
                df_new["nome_capital"] = np.nan
            
            if "cnpj" not in df_new.columns:
                df_new["cnpj"] = np.nan
            
            # Padronizar colunas (garantir ordem e tipos)
            df_new = df_new[["id", "data", "empresa", "nome_capital", "cnpj"]]
            
            # Converter para string para facilitar a comparação
            df_new['empresa'] = df_new['empresa'].astype(str)
            
            try:
                # Tentar baixar o arquivo consolidado do SharePoint
                file_content = sp_client.download_file(SHAREPOINT_FILE_PATH)
                
                # Salvar temporariamente para abrir com pandas
                temp_filepath = os.path.join(app.config['DOWNLOAD_FOLDER'], 'temp_consolidado.xlsx')
                with open(temp_filepath, 'wb') as f:
                    f.write(file_content)
                
                # Ler o arquivo consolidado
                df_consolidado = pd.read_excel(temp_filepath)
                
                # Converter coluna empresa para string
                df_consolidado['empresa'] = df_consolidado['empresa'].astype(str)
                
                # Remover duplicatas baseado na coluna 'empresa'
                df_combined = pd.concat([df_consolidado, df_new])
                df_combined = df_combined.drop_duplicates(subset=['empresa'], keep='first')
                
                # Ordenar por id
                if 'id' in df_combined.columns:
                    df_combined = df_combined.sort_values('id')
                
            except Exception as e:
                print(f"Arquivo consolidado não encontrado ou erro: {str(e)}")
                # Se o arquivo não existe, usar apenas o novo
                df_combined = df_new
            
            # Salvar o arquivo consolidado localmente
            output_filepath = os.path.join(app.config['DOWNLOAD_FOLDER'], 'prospec_consolidado.xlsx')
            df_combined.to_excel(output_filepath, index=False)
            
            # Fazer upload do arquivo consolidado para o SharePoint
            with open(output_filepath, 'rb') as f:
                sp_client.upload_file(f.read(), SHAREPOINT_FILE_PATH)
            
            flash('Arquivo processado e consolidado com sucesso')
            
        except Exception as e:
            flash(f'Erro ao processar o arquivo: {str(e)}')
            print(f"Erro detalhado: {str(e)}")
        
        return redirect(url_for('index'))
    
    flash('Tipo de arquivo não permitido')
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
    if 'sharepoint_email' not in session:
        return redirect(url_for('login'))
    
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