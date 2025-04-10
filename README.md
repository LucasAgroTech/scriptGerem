# Sistema de Matching com Flask e Tailwind CSS

Um sistema web moderno para upload de planilhas e geração de matches, desenvolvido com Flask e Tailwind CSS.

## Estrutura do Projeto

```
projeto/
│
├── app.py                 # Aplicação Flask principal
├── templates/             # Templates HTML
│   └── index.html         # Página principal
├── uploads/               # Diretório para arquivos enviados
└── downloads/             # Diretório para arquivos para download
```

## Requisitos

- Python 3.8+
- Flask
- pandas
- openpyxl (para trabalhar com arquivos Excel)

## Instalação

1. Clone este repositório ou baixe os arquivos
2. Crie um ambiente virtual (recomendado)

```bash
python -m venv venv
```

3. Ative o ambiente virtual

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

4. Instale as dependências

```bash
pip install flask pandas openpyxl
```

## Execução

1. Execute a aplicação Flask

```bash
python app.py
```

2. Acesse a aplicação no navegador: `http://127.0.0.1:5000`

## Funcionalidades

- **Upload Prospec Gerem**: Envie planilhas com dados para processamento inicial
- **Download de Matches**: Baixe os possíveis matches encontrados para validação
- **Upload de Excel Validado**: Envie planilhas com matches validados
- **Download de Matches Finais**: Baixe o resultado final após a validação

## Personalização

O design utiliza Tailwind CSS via CDN. Para personalizar:

1. Modifique o arquivo `templates/index.html`
2. Ajuste as cores e estilos no objeto `tailwind.config`
3. Adicione ou remova classes do Tailwind conforme necessário

## Notas de Implementação

- A aplicação cria automaticamente as pastas `uploads` e `downloads` se não existirem
- Apenas arquivos com extensões .xlsx, .xls e .csv são permitidos
- Para implementar a lógica de negócios específica, modifique as funções nas rotas no arquivo `app.py`