from office365.runtime.auth.user_credential import UserCredential
from office365.sharepoint.client_context import ClientContext
from office365.sharepoint.files.file import File
import pandas as pd
import io
import os
from urllib.parse import urlparse

class SharePointClient:
    def __init__(self, site_url, username, password):
        """Inicializa o cliente do SharePoint com as credenciais do usuário."""
        try:
            self.credentials = UserCredential(username, password)
            self.ctx = ClientContext(site_url).with_credentials(self.credentials)
            
            # Testar a conexão
            self.ctx.load(self.ctx.web)
            self.ctx.execute_query()
            print(f"Conexão estabelecida com: {site_url}")
            
            # Extrair o nome do site do URL
            parsed_url = urlparse(site_url)
            path_parts = parsed_url.path.strip('/').split('/')
            if len(path_parts) >= 2 and path_parts[0] == 'sites':
                self.site_name = path_parts[1]
            else:
                self.site_name = path_parts[-1] if path_parts else ""
            print(f"Nome do site detectado: {self.site_name}")
            
            # Armazenar a URL do site
            self.site_url = site_url
            
            # Detectar a biblioteca de documentos padrão
            self.doc_library = self._detect_document_library()
            print(f"Biblioteca de documentos detectada: {self.doc_library}")
        except Exception as e:
            raise Exception(f"Erro ao conectar ao SharePoint: {str(e)}")
    
    def _detect_document_library(self):
        """Detecta a biblioteca de documentos padrão."""
        try:
            # Lista de possíveis nomes de bibliotecas de documentos
            common_names = ["Shared Documents", "Documents", "Documentos Compartilhados", "Documentos"]
            
            # Obter as listas e bibliotecas do site
            lists = self.ctx.web.lists
            self.ctx.load(lists)
            self.ctx.execute_query()
            
            # Procurar por bibliotecas conhecidas
            for lst in lists:
                if lst.title in common_names:
                    return lst.title
            
            # Se não encontrou, usar o primeiro que parece ser uma biblioteca
            for lst in lists:
                if lst.base_template == 101:  # Biblioteca de documentos
                    return lst.title
            
            # Valor padrão se nenhuma biblioteca foi encontrada
            return "Shared Documents"
        except Exception as e:
            print(f"Erro ao detectar biblioteca de documentos: {str(e)}")
            return "Shared Documents"
    
    def _get_files_list(self, folder_name):
        """Obtém a lista de arquivos em uma pasta."""
        conn = self.ctx
        target_folder_url = f'{self.doc_library}/{folder_name}'
        root_folder = conn.web.get_folder_by_server_relative_url(target_folder_url)
        root_folder.expand(["Files", "Folders"]).get().execute_query()
        return root_folder.files
    
    def download_file(self, file_path):
        """
        Baixa um arquivo do SharePoint usando o caminho relativo.
        
        Args:
            file_path: Caminho relativo do arquivo (pasta/arquivo.xlsx)
            
        Returns:
            bytes: Conteúdo do arquivo
        """
        try:
            # Separar o caminho em pasta e nome do arquivo
            folder_path = os.path.dirname(file_path)
            file_name = os.path.basename(file_path)
            
            print(f"Baixando arquivo '{file_name}' da pasta '{folder_path}'")
            
            # Usar a abordagem que funciona em dados_app/office365_api/office365_api.py
            file_url = f'/sites/{self.site_name}/{self.doc_library}/{folder_path}/{file_name}'
            print(f"URL do arquivo: {file_url}")
            
            # Baixar o arquivo usando File.open_binary
            file = File.open_binary(self.ctx, file_url)
            
            if file and file.content:
                print(f"Arquivo baixado com sucesso: {file_path}")
                return file.content
            else:
                raise Exception(f"Arquivo vazio ou não encontrado: {file_path}")
        
        except Exception as e:
            # Tentar abordagem alternativa com caminhos diferentes
            try:
                print("Tentando abordagem alternativa...")
                
                # Tentar construir diferentes URLs possíveis, começando com o formato que funcionou para upload
                possible_urls = [
                    f'/sites/{self.site_name}/Documentos Compartilhados/{folder_path}/{file_name}',
                    f'/sites/{self.site_name}/Shared Documents/{folder_path}/{file_name}',
                    f'/sites/{self.site_name}/Documents/{folder_path}/{file_name}',
                    f'/sites/{self.site_name}/Documentos/{folder_path}/{file_name}',
                    f'{self.doc_library}/{folder_path}/{file_name}',
                    f'{self.doc_library}/{file_path}',
                    f'Shared Documents/{file_path}',
                    f'Documents/{file_path}',
                    f'Documentos Compartilhados/{file_path}',
                    f'Documentos/{file_path}'
                ]
                
                for url in possible_urls:
                    try:
                        print(f"Tentando URL: {url}")
                        file = File.open_binary(self.ctx, url)
                        if file and file.content:
                            print(f"Arquivo baixado com sucesso usando URL: {url}")
                            return file.content
                    except Exception as url_error:
                        print(f"Falha com URL {url}: {str(url_error)}")
                        continue
                
                raise Exception(f"Todas as tentativas de download falharam para: {file_path}")
            except Exception as alt_error:
                raise Exception(f"Erro ao baixar arquivo: {str(e)} / Alternativa: {str(alt_error)}")
    
    def upload_file(self, file_content, file_path):
        """
        Faz upload de um arquivo para o SharePoint.
        
        Args:
            file_content: Conteúdo do arquivo em bytes
            file_path: Caminho relativo de destino no SharePoint (pasta/arquivo.xlsx)
            
        Returns:
            bool: True se o upload for bem-sucedido
        """
        try:
            # Separar o caminho em pasta e nome do arquivo
            folder_path = os.path.dirname(file_path)
            file_name = os.path.basename(file_path)
            
            print(f"Fazendo upload de '{file_name}' para a pasta '{folder_path}'")
            
            # Usar a mesma abordagem que é usada em dados_app/office365_api/office365_api.py
            target_folder_url = f'/sites/{self.site_name}/{self.doc_library}'
            if folder_path:
                target_folder_url += f'/{folder_path}'
            
            # Obter a pasta e fazer upload do arquivo
            target_folder = self.ctx.web.get_folder_by_server_relative_path(target_folder_url)
            target_folder.upload_file(file_name, file_content).execute_query()
            
            print(f"Upload concluído com sucesso: {file_path}")
            return True
        except Exception as e:
            # Tentar abordagem alternativa
            try:
                print("Tentando abordagem alternativa para upload...")
                
                # Tentar com diferentes caminhos de pasta
                possible_urls = [
                    f'/sites/{self.site_name}/{self.doc_library}',
                    f'/sites/{self.site_name}/Shared Documents',
                    f'/sites/{self.site_name}/Documents',
                    f'/sites/{self.site_name}/Documentos Compartilhados',
                    f'/sites/{self.site_name}/Documentos',
                    f'/{self.doc_library}'
                ]
                
                if folder_path:
                    possible_urls = [f"{url}/{folder_path}" for url in possible_urls]
                
                for url in possible_urls:
                    try:
                        print(f"Tentando URL: {url}")
                        target_folder = self.ctx.web.get_folder_by_server_relative_path(url)
                        target_folder.upload_file(file_name, file_content).execute_query()
                        print(f"Upload concluído com sucesso usando URL: {url}")
                        return True
                    except Exception as url_error:
                        print(f"Falha com URL {url}: {str(url_error)}")
                        continue
                
                raise Exception("Todas as tentativas de upload falharam")
            except Exception as alt_error:
                raise Exception(f"Erro ao fazer upload: {str(e)} / Alternativa: {str(alt_error)}")
    
    def get_excel_data(self, file_path, sheet_name):
        """
        Lê dados de uma planilha Excel do SharePoint.
        
        Args:
            file_path: Caminho relativo do arquivo Excel (pasta/arquivo.xlsx)
            sheet_name: Nome da aba da planilha
            
        Returns:
            list: Lista de dicionários com os dados da planilha
        """
        try:
            # Baixar o arquivo
            file_content = self.download_file(file_path)
            
            # Usar pandas para ler o Excel
            excel_file = io.BytesIO(file_content)
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            
            # Converter para lista de dicionários
            records = df.to_dict('records')
            
            print(f"Lidos {len(records)} registros da planilha {sheet_name}")
            return records
        except Exception as e:
            raise Exception(f"Erro ao ler dados do Excel: {str(e)}")
    
    def update_excel_data(self, file_path, sheet_name, data, id_column=None):
        """
        Atualiza dados em uma planilha Excel do SharePoint.
        
        Args:
            file_path: Caminho relativo do arquivo Excel (pasta/arquivo.xlsx)
            sheet_name: Nome da aba a ser atualizada
            data: Dados para atualização (dict para registro único, list para múltiplos)
            id_column: Nome da coluna de ID para atualização de registro específico
            
        Returns:
            bool: True se a atualização for bem-sucedida
        """
        try:
            # Baixar o arquivo
            file_content = self.download_file(file_path)
            
            # Ler todas as abas do Excel
            excel_file = io.BytesIO(file_content)
            xlsx = pd.ExcelFile(excel_file)
            sheet_names = xlsx.sheet_names
            
            # Criar um buffer para o novo arquivo
            output = io.BytesIO()
            
            # Criar um escritor Excel
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Processar cada aba
                for sheet in sheet_names:
                    # Ler a aba atual
                    df = pd.read_excel(excel_file, sheet_name=sheet)
                    
                    # Se for a aba que queremos atualizar
                    if sheet == sheet_name:
                        if isinstance(data, dict) and id_column is not None:
                            # Atualizar um registro específico
                            idx = df[df[id_column] == data[id_column]].index
                            if len(idx) > 0:
                                # Atualizar registro existente
                                for key, value in data.items():
                                    df.loc[idx[0], key] = value
                            else:
                                # Adicionar novo registro
                                df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
                        elif isinstance(data, list):
                            # Substituir todos os dados
                            df = pd.DataFrame(data)
                        else:
                            raise ValueError("Formato de dados inválido para atualização")
                    
                    # Salvar a aba no novo arquivo
                    df.to_excel(writer, sheet_name=sheet, index=False)
            
            # Obter o conteúdo atualizado
            output.seek(0)
            updated_content = output.getvalue()
            
            # Fazer upload do arquivo atualizado
            self.upload_file(updated_content, file_path)
            
            return True
        except Exception as e:
            raise Exception(f"Erro ao atualizar planilha Excel: {str(e)}")
    
    def get_project_by_id(self, excel_path, project_id):
        """Obtém um projeto específico pelo ID."""
        try:
            projects = self.get_excel_data(excel_path, 'projetos')
            for project in projects:
                if str(project.get('id')) == str(project_id):
                    return project
            return None
        except Exception as e:
            raise Exception(f"Erro ao obter projeto: {str(e)}")
    
    def get_categorization_by_project_id(self, excel_path, project_id):
        """Obtém a categorização de um projeto pelo ID."""
        try:
            categories = self.get_excel_data(excel_path, 'categorias')
            for category in categories:
                if str(category.get('id_projeto')) == str(project_id):
                    return category
            return None
        except Exception as e:
            raise Exception(f"Erro ao obter categorização: {str(e)}")
    
    def log_activity(self, log_file_path, user, action, details=None):
        """
        Registra uma atividade no arquivo de logs.
        
        Args:
            log_file_path: Caminho relativo do arquivo de logs no SharePoint
            user: Usuário que realizou a ação
            action: Tipo de ação realizada
            details: Detalhes adicionais (opcional)
            
        Returns:
            bool: True se o registro foi bem-sucedido
        """
        try:
            import datetime
            import pandas as pd
            import io
            
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Criar um novo registro de log
            log_entry = {
                'timestamp': timestamp,
                'user': user,
                'action': action,
                'details': details if details else ''
            }
            
            # Verificar se o arquivo de logs já existe
            try:
                # Tentar baixar o arquivo existente
                file_content = self.download_file(log_file_path)
                
                # Ler o arquivo existente
                excel_file = io.BytesIO(file_content)
                df_logs = pd.read_excel(excel_file)
                
                # Adicionar o novo registro
                df_logs = pd.concat([df_logs, pd.DataFrame([log_entry])], ignore_index=True)
                
            except Exception as e:
                print(f"Arquivo de logs não encontrado, criando novo: {str(e)}")
                # Criar um novo DataFrame com o registro
                df_logs = pd.DataFrame([log_entry])
            
            # Salvar o DataFrame atualizado em um buffer
            output = io.BytesIO()
            df_logs.to_excel(output, index=False)
            output.seek(0)
            
            # Fazer upload do arquivo atualizado
            self.upload_file(output.getvalue(), log_file_path)
            
            print(f"Log registrado com sucesso: {action} por {user} em {timestamp}")
            return True
            
        except Exception as e:
            print(f"Erro ao registrar log: {str(e)}")
            return False
    
    def get_latest_log(self, log_file_path):
        """
        Obtém o registro de log mais recente.
        
        Args:
            log_file_path: Caminho relativo do arquivo de logs no SharePoint
            
        Returns:
            dict: Registro de log mais recente ou None se não houver registros
        """
        try:
            # Baixar o arquivo de logs
            file_content = self.download_file(log_file_path)
            
            # Ler o arquivo
            excel_file = io.BytesIO(file_content)
            df_logs = pd.read_excel(excel_file)
            
            if len(df_logs) == 0:
                return None
            
            # Ordenar por timestamp (mais recente primeiro)
            df_logs['timestamp'] = pd.to_datetime(df_logs['timestamp'])
            df_logs = df_logs.sort_values('timestamp', ascending=False)
            
            # Retornar o registro mais recente como dicionário
            latest_log = df_logs.iloc[0].to_dict()
            return latest_log
            
        except Exception as e:
            print(f"Erro ao obter último log: {str(e)}")
            return None
