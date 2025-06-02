import os
import datetime
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
from office365_api.download_files import get_file
from office365_api.upload_files import upload_files
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import inspect

# carregar .env e tudo mais
load_dotenv()
ROOT = os.getenv('ROOT')

# Adiciona o diretório correto ao sys.path
# PATH_OFFICE = os.path.abspath(os.path.join(ROOT, 'office365_api'))
# sys.path.append(PATH_OFFICE)

#Definição dos caminhos do SHAREPOINT
SHAREPOINT_SITE = os.getenv('sharepoint_url_site')
SHAREPOINT_SITE_NAME = os.getenv('sharepoint_site_name')
SHAREPOINT_DOC = os.getenv('sharepoint_doc_library')

#Definição das pastas locais
STEP1 = os.path.join(ROOT, "step_1_data_raw")
STEP2 = os.path.join(ROOT, "step_2_stage_area")
STEP3 = os.path.join(ROOT, "step_3_data_processed")
UP_SHAREPOINT = os.path.join(ROOT, "up_sharepoint")

def puxar_planilhas():    
    apagar_arquivos_pasta(STEP1)
    apagar_arquivos_pasta(STEP2)
    apagar_arquivos_pasta(STEP3)
    apagar_arquivos_pasta(UP_SHAREPOINT)

    get_file('apuracao_resultados_2024.xlsx', 'DWPII/gerem', STEP1)
    get_file('gerem_apuracao_validacao.xlsx', 'DWPII/gerem', STEP1)
    get_file('prospeccao_prospeccao.xlsx', 'DWPII/srinfo', STEP1)
    get_file('negociacoes_empresas.xlsx', 'DWPII/srinfo', STEP1)
    get_file('portfolio.xlsx', 'DWPII/srinfo', STEP1)
    get_file('info_empresas.xlsx', 'DWPII/srinfo', STEP1)
    get_file('negociacoes_negociacoes.xlsx', 'DWPII/srinfo', STEP1)
    print("OK - " + inspect.currentframe().f_code.co_name)

def apagar_arquivos_pasta(caminho_pasta):
    try:
        # Verifica se o caminho é válido
        if not os.path.isdir(caminho_pasta):
            print(f"O caminho {caminho_pasta} não é uma pasta válida.")
            return
        
        # Lista todos os arquivos na pasta
        arquivos = os.listdir(caminho_pasta)
        
        # Apaga cada arquivo na pasta
        for arquivo in arquivos:
            caminho_arquivo = os.path.join(caminho_pasta, arquivo)
            if os.path.isfile(caminho_arquivo):
                os.remove(caminho_arquivo)
    except Exception as e:
        print(f"Ocorreu um erro ao apagar os arquivos: {e}")

def stage_area_negociacao_nome_empresa():
    try:
        """
        Função para incluir a coluna nome_empresa na planilha e data de início da negociação em negociacoes_empresas.

        Retorno:
        Cria o arquivo negociacoes_empresas_nome.
        """

        # Ler os arquivos
        df_negociacoes_empresas = pd.read_excel(PATH_NEGOCIACOES_EMPRESAS)
        df_informacoes_empresas = pd.read_excel(PATH_INFORMACOES_EMPRESAS)
        df_negociacoes_negociacoes = pd.read_excel(PATH_NEGOCIACOES_NEGOCIACOES)

        # Fazer o merge usando 'cnpj' como chave
        df_merged = pd.merge(
            df_negociacoes_empresas,
            df_informacoes_empresas[['cnpj', 'razao_social']],
            on='cnpj',
            how='left'
        )

        # Fazer o merge usando 'cnpj' como chave
        df_merged_data = pd.merge(
            df_merged,
            df_negociacoes_negociacoes,
            on='codigo_negociacao',
            how='left'
        )

        # Filtrar as linhas pelo período especificado
        data_menor, data_maior = maior_menor_data(PATH_GEREM_INTERACAO, "data_interacao")
        df_merged_data = df_merged_data[(df_merged_data['data_prim_ver_prop_tec'] >= pd.to_datetime(data_menor))]

        # Salvar o arquivo atualizado, substituindo o original
        df_merged_data.to_excel(PATH_NEGOCIACOES_EMPRESAS_NOME, index=False)
        print("OK - " + inspect.currentframe().f_code.co_name)

    except Exception as e:
        print(f"Erro ao processar: {e}")

def stage_area_apuracao_resultados():
    """
    Função para selecionar apenas as colunas desejadas, ajustar a ordem, renomear colunas
    e realizar ajustes no DataFrame da aba 'resultados_2024'. Além disso, salva os dados da aba
    'empresas_nome_capital' sem modificações.

    Retorno:
    None
    """

    try:
        # Lê as abas do arquivo Excel
        abas = pd.read_excel(PATH_RAW_GEREM_INTERACOES, sheet_name=None)

        # Processar a aba 'resultados_2024'
        if 'resultados_2024' in abas:
            df_resultados = abas['resultados_2024']

            # Dicionário com as colunas de interesse, na ordem desejada, e seus novos nomes
            colunas_interesse_ordem_novoNome = {
                "ID": "id_gerem",
                "Data": "data_interacao",
                "TIPO DE AÇÃO": "tipo_interacao",
                "Formato": "formato",
                "DESCRIÇÃO DA AÇÃO": "descricao",
                "NOME DA EMPRESA": "empresa",
                "Responsável EMBRAPII": "responsavel_embrapii"
            }

            # Selecionar as colunas de interesse, reordenar e renomear
            df_resultados = df_resultados[list(colunas_interesse_ordem_novoNome.keys())]
            df_resultados = df_resultados.rename(columns=colunas_interesse_ordem_novoNome)

            # Adicionar a coluna 'tipo_acao' com valor "Interação GEREM" para todas as linhas
            df_resultados.insert(1, 'tipo_acao', 'Interação GEREM')

            # Remover registros duplicados considerando todas as colunas
            df_resultados = df_resultados.drop_duplicates()

            # Salvar o DataFrame ajustado da aba 'resultados_2024'
            pasta_saida = "step_2_stage_area"
            os.makedirs(pasta_saida, exist_ok=True)  # Garantir que a pasta exista
            caminho_saida_resultados = os.path.join(pasta_saida, "gerem_interacao.xlsx")
            df_resultados.to_excel(caminho_saida_resultados, index=False)

        # Salvar os dados da aba 'empresas_nome_capital' sem modificações
        if 'empresas_nome_capital' in abas:
            df_empresas = abas['empresas_nome_capital']
            caminho_saida_empresas = os.path.join(pasta_saida, "empresa_nome_capital.xlsx")
            df_empresas.to_excel(caminho_saida_empresas, index=False)
        
        print("OK - " + inspect.currentframe().f_code.co_name)

    except Exception as e:
        print(f"Erro ao processar o arquivo: {e}")

def stage_incluir_nome_capital():
    """
    Função para incluir a coluna empresa_nome_capital na planilha gerem_interacao.

    Retorno:
    Substitui o arquivo gerem_interacao com a nova coluna empresa_nome_capital.
    """

    try:
        # Carregar os arquivos Excel
        df_gerem_interacao = pd.read_excel(PATH_GEREM_INTERACAO)
        df_nome_capital = pd.read_excel(PATH_NOME_CAPITAL)

        # Garantir que a chave de correspondência esteja em ambos os DataFrames
        if 'empresa' not in df_gerem_interacao.columns or 'gerem_empresa' not in df_nome_capital.columns:
            raise ValueError("Chaves de correspondência não encontradas nas planilhas.")

        # Criar um dicionário de correspondência {gerem_empresa: nome_capital}
        mapa_nome_capital = dict(zip(df_nome_capital['gerem_empresa'], df_nome_capital['nome_capital']))

        # Adicionar a coluna empresa_nome_capital
        df_gerem_interacao['empresa_nome_capital'] = df_gerem_interacao['empresa'].map(mapa_nome_capital)

        # Substituir valores NaN por valores da coluna 'empresa' (caso não haja correspondência)
        df_gerem_interacao['empresa_nome_capital'] = df_gerem_interacao['empresa_nome_capital'].fillna(df_gerem_interacao['empresa'])

        # Salvar o arquivo atualizado, substituindo o original
        df_gerem_interacao.to_excel(PATH_GEREM_INTERACAO, index=False)
        print("OK - " + inspect.currentframe().f_code.co_name)

    except Exception as e:
        print(f"Erro ao processar os arquivos: {e}")

def maior_menor_data(caminho_arquivo, nome_coluna):
    """
    Função para pegar a maior e menor data presente na planilha.

    Parâmetros:
    caminho_arquivo (str): Caminho completo para o arquivo Excel de entrada.
    nome_coluna (str): Nome da coluna que contém as datas.

    Retorno:
    tuple: Uma tupla contendo a menor e a maior data (data_menor, data_maior).
    """

    try:
        # Lê o arquivo Excel
        df = pd.read_excel(caminho_arquivo)

        # Converter a coluna especificada para datetime
        df[nome_coluna] = pd.to_datetime(df[nome_coluna], errors='coerce')

        # Remover valores inválidos (NaT)
        df = df.dropna(subset=[nome_coluna])

        # Obter a menor e a maior data
        data_menor = df[nome_coluna].min()
        data_maior = df[nome_coluna].max()

        # Retornar as datas como uma tupla
        return data_menor, data_maior

    except Exception as e:
        print(f"Erro ao processar o arquivo: {e}")
        return None

def stage_area_prospeccao(data_inicio, data_fim):
    """
    Função para selecionar apenas as colunas desejadas e o período especificado.

    Parâmetros:
    data_inicio (date): Data de recorte inicial.
    data_fim (date): Data de recorte final.

    Retorno:
    None
    """

    try:
        # Lê o arquivo Excel
        df = pd.read_excel(PATH_RAW_PROSPECCAO)

        # Converter a coluna 'data_prospeccao' para datetime, assumindo o formato 'dd/mm/yyyy'
        df['data_prospeccao'] = pd.to_datetime(df['data_prospeccao'], format='%d/%m/%Y', errors='coerce')

        # Filtrar as linhas pelo período especificado
        df = df[(df['data_prospeccao'] >= pd.to_datetime(data_inicio))]

        # Adicionar a coluna 'tipo_acao' com valor "Prospecção" para todas as linhas
        df.insert(0, 'tipo_acao', 'Prospecção')

        # Remover registros duplicados considerando todas as colunas
        df = df.drop_duplicates()

        # Incluir campo chamado id_prospeccao
        df['id_prospeccao'] = df.apply(
            lambda x: f"{x['data_prospeccao'].strftime('%Y%m%d')}_{x['unidade_embrapii']}_{x['nome_empresa']}", axis=1
        )

        # Salvar o DataFrame resultante em um arquivo Excel
        df.to_excel(PATH_PROSPECCAO, index=False)
        print("OK - " + inspect.currentframe().f_code.co_name)

    except Exception as e:
        print(f"Erro ao processar o arquivo: {e}")

def prospeccao_comparacao():
    """
    Função para apurar a presença de empresas que a GEREM interagiu na base de prospecções do SRInfo,
    utilizando "nome_capital" com maior peso e filtrando por data_interacao e data_prospeccao.

    Retorno:
    Cria planilhas que indicam empresas que tiveram interações com a GEREM e aparecem na base do SRInfo.
    """
    try:
        # Lê os arquivos Excel
        df_gerem = pd.read_excel(PATH_GEREM_INTERACAO)
        df_prospeccao = pd.read_excel(PATH_PROSPECCAO)

        # Criar df_gerem_empresas com as colunas id_gerem, empresa, empresa_nome_capital e data_interacao
        df_gerem_empresas = df_gerem[['id_gerem', 'empresa', 'empresa_nome_capital', 'data_interacao']].copy()

        # Capitalizar os valores em "empresa", "empresa_nome_capital" e "nome_empresa"
        df_gerem_empresas['empresa'] = df_gerem_empresas['empresa'].str.upper()
        df_gerem_empresas['empresa_nome_capital'] = df_gerem_empresas['empresa_nome_capital'].str.upper()
        df_prospeccao['nome_empresa'] = df_prospeccao['nome_empresa'].str.upper()

        # Realizar comparação por verossimilhança
        comparacoes = []
        for _, row_gerem in df_gerem_empresas.iterrows():
            empresa_gerem = row_gerem['empresa']
            nome_capital_gerem = row_gerem['empresa_nome_capital']
            id_gerem = row_gerem['id_gerem']
            data_interacao = row_gerem['data_interacao']

            for _, row_prospeccao in df_prospeccao.iterrows():
                nome_empresa_prospeccao = row_prospeccao['nome_empresa']
                id_prospeccao = row_prospeccao['id_prospeccao']
                data_prospeccao = row_prospeccao['data_prospeccao']

                # Filtro de data: prospecção deve ser posterior à interação
                if pd.to_datetime(data_prospeccao) <= pd.to_datetime(data_interacao):
                    continue

                # Comparação com pesos
                peso_nome_capital = 0.6  # Peso maior para nome_capital
                peso_nome_completo = 0.4  # Peso menor para o nome completo

                # grau_nome_capital = fuzz.token_sort_ratio(nome_capital_gerem, nome_empresa_prospeccao)
                # grau_nome_completo = fuzz.token_sort_ratio(empresa_gerem, nome_empresa_prospeccao)
                # grau_final = (peso_nome_capital * grau_nome_capital) + (peso_nome_completo * grau_nome_completo)
                grau_nome_capital = calcular_grau_verossimilhanca(nome_capital_gerem, nome_empresa_prospeccao)
                grau_final = grau_nome_capital

                if grau_final > 50:  # Considerar apenas comparações acima de 50
                    comparacoes.append({
                        'id_gerem': id_gerem,
                        'gerem_empresa': empresa_gerem,
                        'nome_capital': nome_capital_gerem,
                        'data_interacao': data_interacao,
                        'id_prospeccao': id_prospeccao,
                        'prospeccao_nome_empresa': nome_empresa_prospeccao,
                        'data_prospeccao': data_prospeccao,
                        'grau_verossimilhanca': round(grau_final)
                    })

        # Criar DataFrame com os resultados da comparação
        df_comparacao = pd.DataFrame(comparacoes)

        # Criar a coluna id_unico
        data_base_excel = pd.Timestamp('1900-01-01')
        df_comparacao['data_prospeccao_num'] = pd.to_datetime(df_comparacao['data_prospeccao']).apply(
            lambda x: (x - data_base_excel).days + 2
        )
        df_comparacao['id_unico'] = df_comparacao.apply(
            lambda x: f"{x['id_gerem']}_{x['prospeccao_nome_empresa']}_{x['data_prospeccao_num']}",
            axis=1
        )

        # Remover a coluna auxiliar data_prospeccao_num
        df_comparacao.drop(columns=['data_prospeccao_num'], inplace=True)
        
        # Organizar a ordem das colunas
        colunas = ['id_unico'] + [col for col in df_comparacao.columns if col != 'id_unico']
        df_comparacao = df_comparacao[colunas]

        # Exportar os dados para Excel
        pasta_saida = "step_2_stage_area"
        os.makedirs(pasta_saida, exist_ok=True)  # Garantir que a pasta exista

        # Verificar se o arquivo já existe e apagar, se necessário
        caminho_saida = os.path.join(pasta_saida, "comparacao_gerem_prospeccao.xlsx")
        if os.path.exists(caminho_saida):
            os.remove(caminho_saida)

        # Exportar DataFrames
        # df_prospeccao.to_excel(os.path.join(pasta_saida, "prospeccao_com_ids.xlsx"), index=False)
        df_comparacao.to_excel(caminho_saida, index=False)

        print("OK - " + inspect.currentframe().f_code.co_name)

    except Exception as e:
        print(f"Erro ao processar o arquivo: {e}")

def prospeccao_validacao():
    """
    Função para validar a prospecção de dados, adicionando as colunas 'status_analise_humana' e 'data_analise_humana' no DataFrame de comparação,
    e repassando os valores não analisados para o DataFrame de validação como novas linhas.

    Retorno:
    Cria e salva planilhas atualizadas com os dados analisados e não analisados.
    """
    try:
        # Lê os arquivos Excel
        df_comparacao = pd.read_excel(PATH_PROSPECCAO_COMPARACAO)
        df_validacao = pd.read_excel(PATH_GEREM_APURACAO_VALIDACAO)


        # Criar as colunas 'status_analise_humana' e 'data_analise_humana' em df_comparacao
        def obter_status_e_data(row):
            id_unico = row['id_unico']
            match = df_validacao[df_validacao['id_unico'] == id_unico]
            if not match.empty:
                return (
                    match['status_analise_humana'].iloc[0],
                    match['_validacao_verossimilhanca'].iloc[0],
                    match['data_analise_humana'].iloc[0]
                )
            else:
                return 'Não analisado', None, None

        df_comparacao[['status_analise_humana', 'validacao_verossimilhanca', 'data_analise_humana']] = df_comparacao.apply(
            lambda row: pd.Series(obter_status_e_data(row)), axis=1
        )


        # Identificar valores não validados e adicioná-los ao df_validacao
        nao_analisados = df_comparacao[df_comparacao['status_analise_humana'] == 'Não analisado']
        novas_linhas = nao_analisados[[
            'id_unico', 'id_gerem', 'gerem_empresa', 'nome_capital', 
            'data_interacao', 'id_prospeccao', 'prospeccao_nome_empresa', 
            'data_prospeccao', 'grau_verossimilhanca'
        ]]

        # Concatenar os novos registros ao DataFrame de validação
        df_validacao = pd.concat([df_validacao, novas_linhas], ignore_index=True)

        # Garantir que os campos que não são "Analisado" fiquem com "Não analisado"
        df_validacao['status_analise_humana'] = df_validacao['status_analise_humana'].apply(
            lambda x: 'Analisado' if x == 'Analisado' else 'Não analisado'
        )

        # Remover duplicados não analisados, considerando apenas 'id_unico' e 'id_prospeccao'
        # Criar um DataFrame separado apenas com os "Não analisados"
        df_nao_analisados = df_validacao[df_validacao['status_analise_humana'] == 'Não analisado']

        # Remover duplicatas apenas entre os "Não analisados", mantendo a primeira ocorrência
        df_nao_analisados = df_nao_analisados.drop_duplicates(subset=['id_unico', 'id_prospeccao'], keep='first')

        # Criar um DataFrame separado com os "Analisados" (mantém todas as ocorrências)
        df_analisados = df_validacao[df_validacao['status_analise_humana'] == 'Analisado']

        # Reunir os dois DataFrames novamente
        df_validacao = pd.concat([df_analisados, df_nao_analisados], ignore_index=True)

        # Exportar os dados para Excel
        pasta_saida = "step_3_data_processed"
        os.makedirs(pasta_saida, exist_ok=True)

        # Caminhos
        caminho_analisado = os.path.join(pasta_saida, "prospeccao_apuracao_analisado.xlsx")
        caminho_validacao = os.path.join(PATH_UP_SHAREPOINT, "gerem_apuracao_validacao.xlsx")
        
        # Verificar se os arquivos já existem e apagar, se necessário
        if os.path.exists(caminho_analisado):
            os.remove(caminho_analisado)
        if os.path.exists(caminho_validacao):
            os.remove(caminho_validacao)

        # Salvar os DataFrames
        # df_comparacao.to_excel(caminho_analisado, index=False)
        df_comparacao.to_excel(PATH_PROSPECCAO_APURACAO_ANALISADO, index=False)
        df_validacao.to_excel(caminho_validacao, index=False)

        print("OK - " + inspect.currentframe().f_code.co_name)

    except Exception as e:
        print(f"Erro ao processar os dados: {e}")

def prospeccao_id_gerem_causal_provavel():
    """
    Função para identificar o id_gerem anterior mais próximo à data da prospecção
    e criar a coluna id_gerem_causal_provavel com base na lógica definida.
    """
    try:
        # Ler o arquivo
        df_analisado = pd.read_excel(PATH_PROSPECCAO_APURACAO_ANALISADO)

        # Filtrar apenas os casos onde validacao_verossimilhanca = "Sim"
        df_validado = df_analisado[df_analisado['validacao_verossimilhanca'] == "Sim"].copy()

        # Ordenar por id_prospeccao
        df_validado = df_validado.sort_values(by=['id_prospeccao', 'data_interacao'])

        # Função para encontrar o id_gerem_causal_provavel
        def encontrar_id_gerem_causal(grupo):
            # Ordenar o grupo por data_interacao
            grupo = grupo.sort_values(by='data_interacao')

            # Para cada linha, encontrar a data_interacao anterior mais próxima
            causal_ids = []
            for index, row in grupo.iterrows():
                data_prospeccao = row['data_prospeccao']
                linhas_anteriores = grupo[grupo['data_interacao'] < data_prospeccao]

                if not linhas_anteriores.empty:
                    # Encontrar a data mais próxima
                    linha_causal = linhas_anteriores.iloc[-1]  # Última linha antes da data_prospeccao
                    causal_ids.append(linha_causal['id_gerem'])
                else:
                    causal_ids.append(None)

            grupo['id_gerem_causal_provavel'] = causal_ids
            return grupo

        # Aplicar a lógica para cada id_prospeccao
        df_resultado = df_validado.groupby('id_prospeccao').apply(encontrar_id_gerem_causal)

        # Preencher a nova coluna no DataFrame original
        df_analisado = pd.merge(
            df_analisado,
            df_resultado[['id_unico', 'id_gerem_causal_provavel']],
            on='id_unico',
            how='left'
        )

        # Remover dados duplicados considerando todas as colunas
        df_analisado = df_analisado.drop_duplicates(keep='first')

        # Salvar o arquivo atualizado (substituir)
        df_analisado.to_excel(PATH_PROSPECCAO_APURACAO_ANALISADO, index=False)

        print("OK - " + inspect.currentframe().f_code.co_name)

    except Exception as e:
        print(f"Erro ao processar os dados: {e}")

def output_prospeccao():
    """
    Função para criar a planilha com resultados finais da apuração de prospecções.
    """

    try:
        # Ler os arquivos
        df_prospeccao_apurado_e_analisado = pd.read_excel(PATH_PROSPECCAO_APURACAO_ANALISADO)
        df_prospeccao = pd.read_excel(PATH_PROSPECCAO)

        # Filtrar apenas registros com validacao_verossimilhanca = "Sim"
        df_prospeccao_apurado_e_analisado = df_prospeccao_apurado_e_analisado[
            df_prospeccao_apurado_e_analisado['validacao_verossimilhanca'] == "Sim"
        ].copy()

        # Selecionar apenas as colunas desejadas
        df_prospeccao_apurado_e_analisado = df_prospeccao_apurado_e_analisado[
            ['id_gerem', 'data_interacao', 'id_prospeccao', 'id_gerem_causal_provavel']
        ]

        # Filtrar registros onde id_gerem == id_gerem_causal_provavel
        df_prospeccao_apurado_e_analisado = df_prospeccao_apurado_e_analisado[
            df_prospeccao_apurado_e_analisado['id_gerem'] == df_prospeccao_apurado_e_analisado['id_gerem_causal_provavel']
        ]

        # Remover a coluna id_gerem_causal_provavel
        df_prospeccao_apurado_e_analisado.drop(columns=['id_gerem_causal_provavel'], inplace=True)

        # Merge (procv) dos dados de prospecção
        df_prospeccao_apurado_e_analisado = df_prospeccao_apurado_e_analisado.merge(
            df_prospeccao,
            on='id_prospeccao',  # Chave de junção
            how='left'  # Garante que todas as linhas de df_prospeccao_apurado_e_analisado sejam mantidas
        )

        # Salvar o resultado final
        df_prospeccao_apurado_e_analisado.to_excel(PATH_OUTPUT_PROSPECCAO, index=False)

        print("OK - " + inspect.currentframe().f_code.co_name)

    except Exception as e:
        print(f"Erro ao processar os dados: {e}")

def match_negociacao_prospeccao():
    try:
        """
        Função para comparar as prospecções validadas com as negociações e encontrar os matchs.

        Retorno:
        Cria o arquivo match_negociacoes_prospeccoes.
        """

        # Ler os arquivos
        df_prospeccao = pd.read_excel(PATH_OUTPUT_PROSPECCAO)
        df_negociacoes = pd.read_excel(PATH_NEGOCIACOES_EMPRESAS_NOME)

        # Renomear colunas para garantir a correspondência
        df_prospeccao = df_prospeccao.rename(columns={'cnpj_empresa': 'cnpj'})

        # Converter colunas de datas para datetime
        df_prospeccao['data_prospeccao'] = pd.to_datetime(df_prospeccao['data_prospeccao'], format='%d/%m/%Y', errors='coerce')
        df_negociacoes['data_prim_ver_prop_tec'] = pd.to_datetime(df_negociacoes['data_prim_ver_prop_tec'], format='%d/%m/%Y', errors='coerce')

        # Realizar a junção (procv) com base em cnpj e unidade_embrapii
        df_match = df_prospeccao.merge(
            df_negociacoes,
            on=['cnpj', 'unidade_embrapii'],  
            how='inner'  
        )

        # Selecionar as colunas necessárias
        df_match = df_match[
            ['id_prospeccao', 'data_prospeccao', 'codigo_negociacao', 'unidade_embrapii', 'cnpj', 'razao_social', 'data_prim_ver_prop_tec', 'parceria_programa', 'modalidade_financiamento', 'valor_total_plano_trabalho', 'possibilidade_contratacao', 'status', 'objetivos_prop_tec', 'codigo_projeto']
        ]

        # Criar coluna id_correspondencia como um sequencial simples
        df_match.insert(0, 'id_correspondencia', range(1, len(df_match) + 1))

        
        
        # Criar a coluna 'dif_datas' = data_prim_ver_prop_tec - data_prospeccao
        df_match['dif_datas'] = (df_match['data_prim_ver_prop_tec'] - df_match['data_prospeccao']).dt.days
        
        # Remover os registros onde dif_datas < 0 (ou seja, data_prospeccao posterior à data_prim_ver_prop_tec)
        df_match = df_match[df_match['dif_datas'] >= 0]

        # Criar a coluna 'cont_codigo_negociacao' para contar as repetições de cada código de negociação
        df_match['cont_codigo_negociacao'] = df_match.groupby('codigo_negociacao')['codigo_negociacao'].transform('count')

        # Separar registros com e sem repetição de 'codigo_negociacao'
        df_unicos = df_match[df_match['cont_codigo_negociacao'] == 1]
        df_repetidos = df_match[df_match['cont_codigo_negociacao'] > 1]

        # Para os repetidos, selecionar apenas registros com 'data_prospeccao' anterior à 'data_prim_ver_prop_tec' e mais próxima
        def selecionar_mais_proximo(grupo):
            grupo = grupo[grupo['dif_datas'] > 0]  # Apenas onde data_prospeccao < data_prim_ver_prop_tec
            
            if not grupo.empty:
                return grupo.loc[grupo['dif_datas'].idxmin()]  # Escolhe o mais próximo (menor dif_datas positiva)
            
            return None  # Se não houver nenhuma data_prospeccao válida, retorna None
        
        # Aplicar a lógica de seleção para cada 'codigo_negociacao'
        df_repetidos_filtrados = df_repetidos.groupby('codigo_negociacao', group_keys=False).apply(selecionar_mais_proximo).dropna()

        # Combinar os registros únicos com os filtrados
        df_final = pd.concat([df_unicos, df_repetidos_filtrados], ignore_index=True)

        # Remover as colunas auxiliares
        df_final.drop(columns=['dif_datas', 'cont_codigo_negociacao'], inplace=True)


        # Salvar o arquivo atualizado
        df_final.to_excel(PATH_MATCH_NEGOCIACAO_PROSPECCAO, index=False)
        print("OK - " + inspect.currentframe().f_code.co_name)

    except Exception as e:
        print(f"Erro ao processar: {e}")

def output_negociacao():
    try:
        # Ler os arquivos
        df_match = pd.read_excel(PATH_MATCH_NEGOCIACAO_PROSPECCAO)
        df_prospeccao = pd.read_excel(PATH_OUTPUT_PROSPECCAO)

        # Buscar o id_gerem de df_prospeccao usando id_prospeccao como chave
        df_match = df_match.merge(
            df_prospeccao[['id_prospeccao', 'id_gerem']],  # Seleciona apenas as colunas necessárias
            on='id_prospeccao',
            how='left'  # Mantém todos os registros de df_match e adiciona id_gerem correspondente
        )

        # Remover a coluna id_correspondencia
        df_match.drop(columns=['id_correspondencia'], inplace=True)

        # Garantir que 'data_prim_ver_prop_tec' fique na 5ª posição
        colunas = list(df_match.columns)
        colunas.remove('id_gerem')
        colunas.remove('data_prim_ver_prop_tec')

        # Reordenar colunas: id_gerem em 1º, data_prim_ver_prop_tec na 5ª posição
        colunas_ordenadas = ['id_gerem'] + colunas[:3] + ['data_prim_ver_prop_tec'] + colunas[3:]
        df_match = df_match[colunas_ordenadas]

        # Salvar o arquivo atualizado
        df_match.to_excel(PATH_OUTPUT_NEGOCIACAO, index=False)
        print("OK - " + inspect.currentframe().f_code.co_name)

    except Exception as e:
        print(f"Erro ao processar: {e}")

def output_projetos():
    try:
        # Ler os arquivos
        df_negociacao = pd.read_excel(PATH_OUTPUT_NEGOCIACAO)
        df_portfolio = pd.read_excel(PATH_RAW_PORTFOLIO)

        # Selecionar apenas as colunas desejadas de df_negociacao
        df_projetos = df_negociacao[['id_gerem', 'id_prospeccao', 'data_prospeccao', 'codigo_negociacao', 
                                     'data_prim_ver_prop_tec', 'unidade_embrapii', 'codigo_projeto']].copy()

        # Filtrar apenas as linhas onde 'codigo_projeto' não está vazio
        df_projetos = df_projetos[df_projetos['codigo_projeto'].notna() & (df_projetos['codigo_projeto'] != '')]

        # Merge (procv) com df_portfolio puxando todas as colunas baseadas em 'codigo_projeto'
        df_projetos = df_projetos.merge(df_portfolio, on='codigo_projeto', how='left')

        # Salvar o arquivo atualizado
        df_projetos.to_excel(PATH_OUTPUT_PROJETOS, index=False)
        print("OK - " + inspect.currentframe().f_code.co_name)

    except Exception as e:
        print(f"Erro ao processar: {e}")

def calcular_grau_verossimilhanca(base, alvo):
    """
    Calcula a similaridade entre duas strings, priorizando a presença de tokens menores na string maior.

    Parâmetros:
    base (str): String de referência (nome_capital).
    alvo (str): String a ser comparada (nome_empresa_prospeccao).

    Retorno:
    int: Grau de verossimilhança entre 0 e 100.
    """
    # Dividir as strings em tokens
    tokens_base = set(base.split())
    tokens_alvo = set(alvo.split())

    # Verificar se os tokens da base estão no alvo
    correspondencias = tokens_base.intersection(tokens_alvo)

    # Calcular o peso com base na proporção de tokens encontrados
    if tokens_base:
        proporcao = len(correspondencias) / len(tokens_base)  # Proporção de tokens encontrados
    else:
        proporcao = 0

    # Combinar com a similaridade geral do fuzz.token_set_ratio para robustez
    similaridade_geral = fuzz.token_set_ratio(base, alvo)  # Similaridade baseada no conjunto

    # Combinação ponderada
    peso_proporcao = 0.7  # Peso maior para a proporção de tokens
    peso_similaridade = 0.3  # Peso menor para a similaridade geral

    grau_final = (peso_proporcao * proporcao * 100) + (peso_similaridade * similaridade_geral)

    return round(grau_final)

def levar_arquivo_sharepoint():
    upload_files(PATH_UP_SHAREPOINT, "DWPII/gerem", SHAREPOINT_SITE, SHAREPOINT_SITE_NAME, SHAREPOINT_DOC)

#Paths
PATH_RAW_GEREM_INTERACOES = os.path.join(ROOT, "step_1_data_raw", "apuracao_resultados_2024.xlsx")
PATH_RAW_PROSPECCAO = os.path.join(ROOT, "step_1_data_raw", "prospeccao_prospeccao.xlsx")
PATH_RAW_PORTFOLIO = os.path.join(ROOT, "step_1_data_raw", "portfolio.xlsx")
PATH_NOME_CAPITAL = os.path.join(ROOT, "step_2_stage_area", "empresa_nome_capital.xlsx")
PATH_GEREM_INTERACAO = os.path.join(ROOT, "step_2_stage_area", "gerem_interacao.xlsx")
PATH_PROSPECCAO = os.path.join(ROOT, "step_2_stage_area", "srinfo_prospeccao.xlsx")
PATH_PROSPECCAO_COMPARACAO = os.path.join(ROOT, "step_2_stage_area", "comparacao_gerem_prospeccao.xlsx")
PATH_GEREM_APURACAO_VALIDACAO = os.path.join(ROOT, "step_1_data_raw", "gerem_apuracao_validacao.xlsx")
PATH_NEGOCIACOES_NEGOCIACOES = os.path.join(ROOT, "step_1_data_raw", "negociacoes_negociacoes.xlsx")
PATH_NEGOCIACOES_EMPRESAS = os.path.join(ROOT, "step_1_data_raw", "negociacoes_empresas.xlsx")
PATH_INFORMACOES_EMPRESAS = os.path.join(ROOT, "step_1_data_raw", "info_empresas.xlsx")
PATH_NEGOCIACOES_EMPRESAS_NOME = os.path.join(ROOT, "step_2_stage_area", "negociacoes_empresas_nome.xlsx")
PATH_MATCH_NEGOCIACAO_PROSPECCAO = os.path.join(ROOT, "step_2_stage_area", "match_negociacoes_prospeccoes.xlsx")
PATH_NEGOCIACAO_COMPARACAO = os.path.join(ROOT, "step_2_stage_area", "comparacao_gerem_negociacao.xlsx")
PATH_NEGOCIACAO_VALIDACAO = os.path.join(ROOT, "step_1_data_raw", "gerem_validacao_negociacao.xlsx")
PATH_NEGOCIACAO_ANALISADO = os.path.join(ROOT, "step_2_stage_area", "negociacao_analisado.xlsx")
PATH_NEGOCIACAO_VALIDACAO_UP = os.path.join(ROOT, "up_sharepoint", "gerem_validacao_negociacao.xlsx")
PATH_UP_SHAREPOINT = os.path.join(ROOT, "up_sharepoint")
PATH_PROSPECCAO_APURACAO_ANALISADO = os.path.join(ROOT, "step_2_stage_area", "prospeccao_apuracao_analisado.xlsx")
PATH_OUTPUT_PROSPECCAO = os.path.join(ROOT, "step_3_data_processed", "output_prospeccao.xlsx")
PATH_OUTPUT_NEGOCIACAO = os.path.join(ROOT, "step_3_data_processed", "output_negociacao.xlsx")
PATH_OUTPUT_PROJETOS = os.path.join(ROOT, "step_3_data_processed", "output_projeto.xlsx")

def main():
    """
    Função para estimar o impacto das ações de prospecção de empresas realizadas pela GEREM --> prospecções, negociações e projetos (SRInfo).
    """
    # Registrar o início do processo
    data_hora_inicio = datetime.now()
    print(f"Processo iniciado em: {data_hora_inicio.strftime('%Y-%m-%d %H:%M:%S')}")

    # 1 Baixar a planilha de registros
    puxar_planilhas()

    # 2. Tratar as bases de dados
    # 2.1. Gerem > Interações
    stage_area_apuracao_resultados()

    # 2.2. SRInfo > Prospecção
    data_menor, data_maior = maior_menor_data(PATH_GEREM_INTERACAO, "data_interacao")
    stage_area_prospeccao(data_menor, data_maior)
    
    # 2.3. Incluir o nome capital em gerem_interacao
    stage_incluir_nome_capital()

    # 2.4. Incluir nome da empresa e data da negociação em negociacoes_empresa
    stage_area_negociacao_nome_empresa()

    # # 3. Apurar resultados

    # 3.1. Apuração de prospecções
    prospeccao_comparacao()
    prospeccao_validacao()
    prospeccao_id_gerem_causal_provavel()
    output_prospeccao()

    # 3.2. Apuração de negociações
    match_negociacao_prospeccao()
    output_negociacao()

    # 3.3. Apuração projetos
    output_projetos()

    # Levar arquivos para o sharepoint
    levar_arquivo_sharepoint()

    # Registrar o término do processo
    data_hora_fim = datetime.now()
    print(f"Processo finalizado em: {data_hora_fim.strftime('%Y-%m-%d %H:%M:%S')}")

    # Exibir o tempo total de execução
    tempo_total = data_hora_fim - data_hora_inicio
    print(f"Tempo total de execução: {tempo_total}")

  
if __name__ == "__main__":
    main()