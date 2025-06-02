from flask import Flask, render_template, request, send_file, redirect, url_for, session, flash, jsonify
import os
import pandas as pd
import numpy as np
from werkzeug.utils import secure_filename
import uuid
from pathlib import Path
import sys
import datetime
import io
from dotenv import load_dotenv
import json

# Adicionar diretório raiz ao sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Importar módulos
from office365_api.sharepoint_client import SharePointClient
from routes.sharepoint_matching import SharePointMatcher
from routes.download_routes import register_download_routes
from routes.api_routes import register_api_routes

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
SHAREPOINT_LOGS_PATH = 'General/Lucas Pinheiro/scriptGerem/logs.xlsx'
SHAREPOINT_UPLOADS_PATH = 'General/Lucas Pinheiro/scriptGerem/uploads'
SHAREPOINT_METADATA_PATH = 'General/Lucas Pinheiro/scriptGerem/metadata.json'

# Registrar rotas de download e API
app = register_download_routes(app)
app = register_api_routes(app)

# Configurar o método get_sharepoint_client como um método do app
app.get_sharepoint_client = lambda: get_sharepoint_client()

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
    
    # Registrar o acesso à página principal
    try:
        # Obter cliente SharePoint
        sp_client = get_sharepoint_client()
        if sp_client:
            current_user = session['sharepoint_email']
            log_details = "Acesso à página principal"
            sp_client.log_activity(
                SHAREPOINT_LOGS_PATH,
                current_user,
                "page_view",
                log_details
            )
    except Exception as e:
        print(f"Erro ao registrar acesso à página: {str(e)}")
    
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
            
            # Registrar o login no arquivo de logs
            log_details = "Login bem-sucedido"
            sp_client.log_activity(
                SHAREPOINT_LOGS_PATH,
                email,
                "login",
                log_details
            )
            
            # Redirecionar para a página principal
            return redirect(url_for('index'))
            
        except Exception as e:
            error = f"Falha na autenticação. Verifique suas credenciais."
            print(f"Erro de login: {str(e)}")
    
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    """Encerra a sessão do usuário"""
    # Registrar o logout no arquivo de logs, se o usuário estiver logado
    if 'sharepoint_email' in session:
        try:
            # Obter cliente SharePoint
            sp_client = get_sharepoint_client()
            if sp_client:
                current_user = session['sharepoint_email']
                log_details = "Logout"
                sp_client.log_activity(
                    SHAREPOINT_LOGS_PATH,
                    current_user,
                    "logout",
                    log_details
                )
        except Exception as e:
            print(f"Erro ao registrar logout: {str(e)}")
    
    # Limpar a sessão
    session.clear()
    return redirect(url_for('login'))

def sync_metadata_with_sharepoint():
    """Sincroniza o arquivo de metadados local com o SharePoint"""
    try:
        # Obter cliente SharePoint
        sp_client = get_sharepoint_client()
        if not sp_client:
            print("Erro de conexão com o SharePoint ao sincronizar metadados")
            return False
        
        # Caminho do arquivo de metadados local
        metadata_path = os.path.join(app.config['UPLOAD_FOLDER'], 'metadata.json')
        
        # Verificar se o arquivo de metadados existe localmente
        if not os.path.exists(metadata_path):
            # Se não existir localmente, criar um arquivo vazio
            metadata = {"files": []}
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=4)
        
        # Ler o arquivo de metadados local
        with open(metadata_path, 'r') as f:
            local_metadata = json.load(f)
        
        # Tentar baixar o arquivo de metadados do SharePoint
        try:
            file_content = sp_client.download_file(SHAREPOINT_METADATA_PATH)
            
            # Ler o arquivo de metadados do SharePoint
            sharepoint_metadata = json.loads(file_content.decode('utf-8'))
            
            # Mesclar os metadados (manter todos os arquivos de ambas as fontes)
            # Criar um dicionário para facilitar a busca por saved_filename
            files_dict = {file_info.get('saved_filename'): file_info for file_info in local_metadata.get('files', [])}
            
            # Adicionar ou atualizar arquivos do SharePoint
            for sp_file_info in sharepoint_metadata.get('files', []):
                saved_filename = sp_file_info.get('saved_filename')
                if saved_filename not in files_dict:
                    # Adicionar arquivo que existe apenas no SharePoint
                    local_metadata['files'].append(sp_file_info)
                else:
                    # O arquivo existe em ambos, manter a versão mais recente
                    # (assumindo que o upload_date está no formato correto para comparação)
                    local_date = files_dict[saved_filename].get('upload_date', '')
                    sp_date = sp_file_info.get('upload_date', '')
                    if sp_date > local_date:
                        # Atualizar com a versão do SharePoint
                        for i, file_info in enumerate(local_metadata['files']):
                            if file_info.get('saved_filename') == saved_filename:
                                local_metadata['files'][i] = sp_file_info
                                break
            
        except Exception as e:
            print(f"Arquivo de metadados não encontrado no SharePoint ou erro: {str(e)}")
            # Se o arquivo não existe no SharePoint, usar apenas o local
        
        # Fazer upload do arquivo de metadados atualizado para o SharePoint
        with open(metadata_path, 'r') as f:
            metadata_content = f.read().encode('utf-8')
            sp_client.upload_file(metadata_content, SHAREPOINT_METADATA_PATH)
        
        return True
        
    except Exception as e:
        print(f"Erro ao sincronizar metadados: {str(e)}")
        return False

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
        # Obter cliente SharePoint
        sp_client = get_sharepoint_client()
        if not sp_client:
            flash('Erro de conexão com o SharePoint')
            return redirect(url_for('index'))
        
        # Gerar nome de arquivo com timestamp para evitar sobrescrever arquivos
        original_filename = secure_filename(file.filename)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        saved_filename = f"{timestamp}_{original_filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], saved_filename)
        file.save(filepath)
        
        # Registrar metadados do arquivo
        current_user = session['sharepoint_email']
        upload_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Carregar ou criar arquivo de metadados
        metadata_path = os.path.join(app.config['UPLOAD_FOLDER'], 'metadata.json')
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                try:
                    metadata = json.load(f)
                except json.JSONDecodeError:
                    metadata = {"files": []}
        else:
            metadata = {"files": []}
        
        # Adicionar informações do novo arquivo
        file_info = {
            "original_filename": original_filename,
            "saved_filename": saved_filename,
            "upload_date": upload_date,
            "user": current_user,
            "sharepoint_path": f"{SHAREPOINT_UPLOADS_PATH}/{saved_filename}"
        }
        metadata["files"].append(file_info)
        
        # Salvar metadados atualizados
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=4)
        
        # Fazer upload do arquivo original para o SharePoint
        try:
            with open(filepath, 'rb') as f:
                file_content = f.read()
                sharepoint_file_path = f"{SHAREPOINT_UPLOADS_PATH}/{saved_filename}"
                sp_client.upload_file(file_content, sharepoint_file_path)
                print(f"Arquivo original enviado para o SharePoint: {sharepoint_file_path}")
        except Exception as e:
            print(f"Erro ao fazer upload do arquivo original para o SharePoint: {str(e)}")
            # Continuar mesmo se o upload falhar
        
        # Sincronizar metadados com o SharePoint
        try:
            sync_metadata_with_sharepoint()
        except Exception as e:
            print(f"Erro ao sincronizar metadados: {str(e)}")
            # Continuar mesmo se a sincronização falhar
        
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
            
            # Adicionando informações de atualização
            current_time = datetime.datetime.now()
            current_user = session['sharepoint_email']
            user_name = current_user.split('@')[0]  # Pegar parte antes do @
            
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
                
                # Número total de registros
                total_records = len(df_combined)
                
            except Exception as e:
                print(f"Arquivo consolidado não encontrado ou erro: {str(e)}")
                # Se o arquivo não existe, usar apenas o novo
                df_combined = df_new
                total_records = len(df_new)
            
            # Adicionar metadados ao final do arquivo
            df_combined.attrs['last_update'] = current_time.strftime('%Y-%m-%d %H:%M:%S')
            df_combined.attrs['last_update_by'] = user_name
            df_combined.attrs['total_records'] = total_records
            
            # Salvar o arquivo consolidado localmente
            output_filepath = os.path.join(app.config['DOWNLOAD_FOLDER'], 'prospec_consolidado.xlsx')
            df_combined.to_excel(output_filepath, index=False)
            
            # Salvar metadados em um arquivo separado para poder acessá-los depois
            metadata = {
                'last_update': current_time.strftime('%Y-%m-%d %H:%M:%S'),
                'last_update_by': user_name,
                'total_records': total_records
            }
            metadata_filepath = os.path.join(app.config['DOWNLOAD_FOLDER'], 'prospec_metadata.json')
            with open(metadata_filepath, 'w') as f:
                json.dump(metadata, f)
            
            # Fazer upload do arquivo consolidado para o SharePoint
            with open(output_filepath, 'rb') as f:
                sp_client.upload_file(f.read(), SHAREPOINT_FILE_PATH)
            
            # Registrar a atividade no arquivo de logs
            log_details = f"Total de registros: {total_records}, Arquivo: {original_filename}"
            sp_client.log_activity(
                SHAREPOINT_LOGS_PATH,
                current_user,
                "upload_prospec",
                log_details
            )
            
            # Armazenar os metadados na sessão para exibição imediata
            session['prospec_metadata'] = metadata
            
            flash('Arquivo processado e consolidado com sucesso')
            
        except Exception as e:
            flash(f'Erro ao processar o arquivo: {str(e)}')
            print(f"Erro detalhado: {str(e)}")
        
        return redirect(url_for('index'))
    
    flash('Tipo de arquivo não permitido')
    return redirect(url_for('index'))

@app.route('/download_matches')
def download_matches():
    # Verificar se o usuário está logado
    if 'sharepoint_email' not in session:
        return redirect(url_for('login'))
    
    try:
        # Obter cliente SharePoint
        sp_client = get_sharepoint_client()
        if not sp_client:
            flash('Erro de conexão com o SharePoint')
            return redirect(url_for('index'))
        
        # Lógica para gerar o arquivo de matches
        # Se o arquivo já existir:
        # return send_file(os.path.join(app.config['DOWNLOAD_FOLDER'], 'matches.xlsx'))
        
        # Registrar a atividade no arquivo de logs
        current_user = session['sharepoint_email']
        log_details = "Download de matches"
        sp_client.log_activity(
            SHAREPOINT_LOGS_PATH,
            current_user,
            "download_matches",
            log_details
        )
        
    except Exception as e:
        flash(f'Erro ao processar o download: {str(e)}')
        print(f"Erro detalhado: {str(e)}")
    
    # Temporário, apenas para exemplo
    return redirect(url_for('index'))

@app.route('/upload_validated', methods=['POST'])
def upload_validated():
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
        # Obter cliente SharePoint
        sp_client = get_sharepoint_client()
        if not sp_client:
            flash('Erro de conexão com o SharePoint')
            return redirect(url_for('index'))
        
        # Gerar nome de arquivo com timestamp para evitar sobrescrever arquivos
        original_filename = secure_filename(file.filename)
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        saved_filename = f"{timestamp}_{original_filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], saved_filename)
        file.save(filepath)
        
        # Registrar metadados do arquivo
        current_user = session['sharepoint_email']
        upload_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Carregar ou criar arquivo de metadados
        metadata_path = os.path.join(app.config['UPLOAD_FOLDER'], 'metadata.json')
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                try:
                    metadata = json.load(f)
                except json.JSONDecodeError:
                    metadata = {"files": []}
        else:
            metadata = {"files": []}
        
        # Adicionar informações do novo arquivo
        file_info = {
            "original_filename": original_filename,
            "saved_filename": saved_filename,
            "upload_date": upload_date,
            "user": current_user,
            "type": "validated",  # Marcar como arquivo validado
            "sharepoint_path": f"{SHAREPOINT_UPLOADS_PATH}/validated/{saved_filename}"
        }
        metadata["files"].append(file_info)
        
        # Salvar metadados atualizados
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=4)
        
        # Fazer upload do arquivo original para o SharePoint
        try:
            with open(filepath, 'rb') as f:
                file_content = f.read()
                sharepoint_file_path = f"{SHAREPOINT_UPLOADS_PATH}/validated/{saved_filename}"
                sp_client.upload_file(file_content, sharepoint_file_path)
                print(f"Arquivo validado enviado para o SharePoint: {sharepoint_file_path}")
        except Exception as e:
            print(f"Erro ao fazer upload do arquivo validado para o SharePoint: {str(e)}")
            # Continuar mesmo se o upload falhar
        
        # Sincronizar metadados com o SharePoint
        try:
            sync_metadata_with_sharepoint()
        except Exception as e:
            print(f"Erro ao sincronizar metadados: {str(e)}")
            # Continuar mesmo se a sincronização falhar
        
        try:
            # Aqui você pode adicionar sua lógica para processar o arquivo validado
            # Por exemplo: processar_validado(filepath)
            
            # Registrar a atividade no arquivo de logs
            log_details = f"Arquivo validado: {original_filename}"
            sp_client.log_activity(
                SHAREPOINT_LOGS_PATH,
                current_user,
                "upload_validated",
                log_details
            )
            
            flash('Arquivo validado processado com sucesso')
            
        except Exception as e:
            flash(f'Erro ao processar o arquivo validado: {str(e)}')
            print(f"Erro detalhado: {str(e)}")
        
        return redirect(url_for('index'))
    
    flash('Tipo de arquivo não permitido')
    return redirect(url_for('index'))

@app.route('/api/sharepoint_stats')
def sharepoint_stats():
    """Retorna estatísticas do arquivo consolidado"""
    if 'sharepoint_email' not in session:
        return jsonify({'error': 'Não autenticado'}), 401
    
    # Se temos metadados na sessão, usar
    if 'prospec_metadata' in session:
        return jsonify(session['prospec_metadata'])
    
    # Obter cliente SharePoint
    sp_client = get_sharepoint_client()
    if not sp_client:
        return jsonify({'error': 'Erro de conexão com o SharePoint'}), 500
    
    try:
        # Tentar obter o último log de upload_prospec
        latest_upload_log = None
        try:
            # Baixar o arquivo de logs
            file_content = sp_client.download_file(SHAREPOINT_LOGS_PATH)
            
            # Ler o arquivo
            excel_file = io.BytesIO(file_content)
            df_logs = pd.read_excel(excel_file)
            
            if len(df_logs) > 0:
                # Converter timestamp para datetime
                df_logs['timestamp'] = pd.to_datetime(df_logs['timestamp'])
                
                # Filtrar apenas logs de upload_prospec
                upload_logs = df_logs[df_logs['action'] == 'upload_prospec']
                
                if len(upload_logs) > 0:
                    # Ordenar por timestamp (mais recente primeiro)
                    upload_logs = upload_logs.sort_values('timestamp', ascending=False)
                    
                    # Obter o registro mais recente
                    latest_upload_log = upload_logs.iloc[0].to_dict()
        except Exception as log_error:
            print(f"Erro ao obter logs: {str(log_error)}")
        
        # Se encontrou um log de upload, usar suas informações
        if latest_upload_log:
            timestamp = latest_upload_log.get('timestamp')
            user = latest_upload_log.get('user')
            details = latest_upload_log.get('details', '')
            
            # Extrair o total de registros dos detalhes, se disponível
            total_records = 0
            if details and 'Total de registros:' in details:
                try:
                    total_part = details.split('Total de registros:')[1].split(',')[0].strip()
                    total_records = int(total_part)
                except (ValueError, IndexError):
                    total_records = 0
            
            # Criar metadados a partir do log
            metadata = {
                'last_update': timestamp if isinstance(timestamp, str) else str(timestamp),
                'last_update_by': user,
                'total_records': total_records
            }
            
            # Armazenar na sessão para futuras consultas
            session['prospec_metadata'] = metadata
            
            return jsonify(metadata)
        
        # Se não encontrou logs de upload, tentar o método antigo (arquivo Excel)
        try:
            # Tentar baixar o arquivo consolidado do SharePoint
            file_content = sp_client.download_file(SHAREPOINT_FILE_PATH)
            
            # Salvar temporariamente para abrir com pandas
            temp_filepath = os.path.join(app.config['DOWNLOAD_FOLDER'], 'temp_consolidado.xlsx')
            with open(temp_filepath, 'wb') as f:
                f.write(file_content)
            
            # Ler o arquivo consolidado
            df_consolidado = pd.read_excel(temp_filepath)
            
            # Verificar se existem metadados no arquivo
            metadata = {}
            if hasattr(df_consolidado, 'attrs') and 'last_update' in df_consolidado.attrs:
                metadata = {
                    'last_update': df_consolidado.attrs['last_update'],
                    'last_update_by': df_consolidado.attrs['last_update_by'],
                    'total_records': df_consolidado.attrs['total_records']
                }
            else:
                # Se não houver metadados, criar básicos
                metadata = {
                    'last_update': 'Desconhecido',
                    'last_update_by': 'Desconhecido',
                    'total_records': len(df_consolidado)
                }
            
            # Armazenar na sessão para futuras consultas
            session['prospec_metadata'] = metadata
            
            return jsonify(metadata)
            
        except Exception as excel_error:
            print(f"Erro ao obter estatísticas do Excel: {str(excel_error)}")
            raise excel_error
        
    except Exception as e:
        print(f"Erro ao obter estatísticas: {str(e)}")
        return jsonify({
            'last_update': 'Desconhecido',
            'last_update_by': 'Desconhecido',
            'total_records': 0
        })

@app.route('/download_final_matches')
def download_final_matches():
    # Verificar se o usuário está logado
    if 'sharepoint_email' not in session:
        return redirect(url_for('login'))
    
    try:
        # Obter cliente SharePoint
        sp_client = get_sharepoint_client()
        if not sp_client:
            flash('Erro de conexão com o SharePoint')
            return redirect(url_for('index'))
        
        # Lógica para gerar o arquivo final de matches
        # Se o arquivo já existir:
        # return send_file(os.path.join(app.config['DOWNLOAD_FOLDER'], 'final_matches.xlsx'))
        
        # Registrar a atividade no arquivo de logs
        current_user = session['sharepoint_email']
        log_details = "Download de matches finais"
        sp_client.log_activity(
            SHAREPOINT_LOGS_PATH,
            current_user,
            "download_final_matches",
            log_details
        )
        
    except Exception as e:
        flash(f'Erro ao processar o download: {str(e)}')
        print(f"Erro detalhado: {str(e)}")
    
    # Temporário, apenas para exemplo
    return redirect(url_for('index'))

@app.route('/download_uploaded_file/<filename>')
def download_uploaded_file(filename):
    """Rota para download de arquivos individuais que foram enviados"""
    # Verificar se o usuário está logado
    if 'sharepoint_email' not in session:
        return redirect(url_for('login'))
    
    try:
        # Verificar se o arquivo existe
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(filepath):
            flash('Arquivo não encontrado')
            return redirect(url_for('index'))
        
        # Obter o nome original do arquivo a partir dos metadados
        metadata_path = os.path.join(app.config['UPLOAD_FOLDER'], 'metadata.json')
        original_filename = filename  # Valor padrão
        
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                try:
                    metadata = json.load(f)
                    # Procurar pelo arquivo nos metadados
                    for file_info in metadata.get('files', []):
                        if file_info.get('saved_filename') == filename:
                            original_filename = file_info.get('original_filename', filename)
                            break
                except json.JSONDecodeError:
                    pass
        
        # Registrar a atividade no arquivo de logs
        try:
            sp_client = get_sharepoint_client()
            if sp_client:
                current_user = session['sharepoint_email']
                log_details = f"Download de arquivo individual: {original_filename}"
                sp_client.log_activity(
                    SHAREPOINT_LOGS_PATH,
                    current_user,
                    "download_uploaded_file",
                    log_details
                )
        except Exception as log_error:
            print(f"Erro ao registrar log de download: {str(log_error)}")
        
        # Enviar o arquivo para download
        return send_file(
            filepath,
            as_attachment=True,
            download_name=original_filename
        )
        
    except Exception as e:
        flash(f'Erro ao processar o download: {str(e)}')
        print(f"Erro detalhado: {str(e)}")
        return redirect(url_for('index'))

@app.route('/download_template')
def download_template():
    """Rota para download do template vazio para upload"""
    # Verificar se o usuário está logado
    if 'sharepoint_email' not in session:
        return redirect(url_for('login'))
    
    try:
        # Criar um DataFrame vazio com as colunas necessárias
        df_template = pd.DataFrame(columns=["id", "data", "empresa", "nome_capital", "cnpj"])
        
        # Criar um arquivo Excel na memória
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_template.to_excel(writer, index=False)
        
        output.seek(0)
        
        # Registrar a atividade no arquivo de logs
        try:
            sp_client = get_sharepoint_client()
            if sp_client:
                current_user = session['sharepoint_email']
                log_details = "Download do template vazio para upload"
                sp_client.log_activity(
                    SHAREPOINT_LOGS_PATH,
                    current_user,
                    "download_template",
                    log_details
                )
        except Exception as log_error:
            print(f"Erro ao registrar log de download do template: {str(log_error)}")
        
        # Enviar o arquivo para download
        return send_file(
            output,
            as_attachment=True,
            download_name="template_upload.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        flash(f'Erro ao gerar o template: {str(e)}')
        print(f"Erro detalhado: {str(e)}")
        return redirect(url_for('index'))

@app.route('/download_consolidated')
def download_consolidated():
    """Rota para download do arquivo consolidado"""
    # Verificar se o usuário está logado
    if 'sharepoint_email' not in session:
        return redirect(url_for('login'))
    
    try:
        # Verificar se o arquivo existe localmente
        filepath = os.path.join(app.config['DOWNLOAD_FOLDER'], 'prospec_consolidado.xlsx')
        
        # Se não existir localmente, tentar baixar do SharePoint
        if not os.path.exists(filepath):
            sp_client = get_sharepoint_client()
            if not sp_client:
                flash('Erro de conexão com o SharePoint')
                return redirect(url_for('index'))
            
            # Baixar o arquivo do SharePoint
            file_content = sp_client.download_file(SHAREPOINT_FILE_PATH)
            
            # Salvar localmente
            with open(filepath, 'wb') as f:
                f.write(file_content)
        
        # Registrar a atividade no arquivo de logs
        try:
            sp_client = get_sharepoint_client()
            if sp_client:
                current_user = session['sharepoint_email']
                log_details = "Download do arquivo consolidado"
                sp_client.log_activity(
                    SHAREPOINT_LOGS_PATH,
                    current_user,
                    "download_consolidated",
                    log_details
                )
        except Exception as log_error:
            print(f"Erro ao registrar log de download: {str(log_error)}")
        
        # Enviar o arquivo para download
        return send_file(
            filepath,
            as_attachment=True,
            download_name="prospec_consolidado.xlsx"
        )
        
    except Exception as e:
        flash(f'Erro ao processar o download: {str(e)}')
        print(f"Erro detalhado: {str(e)}")
        return redirect(url_for('index'))

@app.route('/api/uploaded_files')
def api_uploaded_files():
    """Retorna a lista de arquivos enviados"""
    if 'sharepoint_email' not in session:
        return jsonify({'error': 'Não autenticado'}), 401
    
    try:
        # Tentar sincronizar metadados com o SharePoint antes de retornar a lista
        try:
            sync_metadata_with_sharepoint()
        except Exception as e:
            print(f"Erro ao sincronizar metadados: {str(e)}")
            # Continuar mesmo se a sincronização falhar
        
        # Verificar se o arquivo de metadados existe
        metadata_path = os.path.join(app.config['UPLOAD_FOLDER'], 'metadata.json')
        if not os.path.exists(metadata_path):
            return jsonify({'files': []})
        
        # Ler o arquivo de metadados
        with open(metadata_path, 'r') as f:
            try:
                metadata = json.load(f)
                # Ordenar arquivos por data de upload (mais recente primeiro)
                files = metadata.get('files', [])
                files.sort(key=lambda x: x.get('upload_date', ''), reverse=True)
                
                # Adicionar flag para indicar se o arquivo está disponível no SharePoint
                for file in files:
                    file['in_sharepoint'] = 'sharepoint_path' in file
                
                return jsonify({'files': files})
            except json.JSONDecodeError:
                return jsonify({'files': []})
    
    except Exception as e:
        print(f"Erro ao obter lista de arquivos: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/download_sharepoint_file/<filename>')
def download_sharepoint_file(filename):
    """Rota para download de arquivos diretamente do SharePoint"""
    # Verificar se o usuário está logado
    if 'sharepoint_email' not in session:
        return redirect(url_for('login'))
    
    try:
        # Obter cliente SharePoint
        sp_client = get_sharepoint_client()
        if not sp_client:
            flash('Erro de conexão com o SharePoint')
            return redirect(url_for('index'))
        
        # Obter o caminho do arquivo no SharePoint a partir dos metadados
        metadata_path = os.path.join(app.config['UPLOAD_FOLDER'], 'metadata.json')
        sharepoint_file_path = None
        original_filename = filename  # Valor padrão
        
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                try:
                    metadata = json.load(f)
                    # Procurar pelo arquivo nos metadados
                    for file_info in metadata.get('files', []):
                        if file_info.get('saved_filename') == filename:
                            sharepoint_file_path = file_info.get('sharepoint_path')
                            original_filename = file_info.get('original_filename', filename)
                            break
                except json.JSONDecodeError:
                    pass
        
        if not sharepoint_file_path:
            # Se não encontrou o caminho nos metadados, usar o caminho padrão
            sharepoint_file_path = f"{SHAREPOINT_UPLOADS_PATH}/{filename}"
        
        # Baixar o arquivo do SharePoint
        file_content = sp_client.download_file(sharepoint_file_path)
        
        # Salvar temporariamente para enviar ao usuário
        temp_filepath = os.path.join(app.config['DOWNLOAD_FOLDER'], f"temp_{filename}")
        with open(temp_filepath, 'wb') as f:
            f.write(file_content)
        
        # Registrar a atividade no arquivo de logs
        try:
            current_user = session['sharepoint_email']
            log_details = f"Download de arquivo do SharePoint: {original_filename}"
            sp_client.log_activity(
                SHAREPOINT_LOGS_PATH,
                current_user,
                "download_sharepoint_file",
                log_details
            )
        except Exception as log_error:
            print(f"Erro ao registrar log de download: {str(log_error)}")
        
        # Enviar o arquivo para download
        return send_file(
            temp_filepath,
            as_attachment=True,
            download_name=original_filename
        )
        
    except Exception as e:
        flash(f'Erro ao baixar arquivo do SharePoint: {str(e)}')
        print(f"Erro detalhado: {str(e)}")
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
