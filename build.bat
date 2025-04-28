@echo off
echo ===== Iniciando processo de build do Matching System =====

echo Criando ambiente virtual...
python -m venv venv

echo Ativando ambiente virtual...
call venv\Scripts\activate

echo Instalando dependencias...
pip install -r requirements.txt

echo Preparando estrutura de diretórios...
if not exist uploads mkdir uploads
if not exist downloads mkdir downloads
if not exist hooks mkdir hooks
if not exist static mkdir static
if not exist static\img mkdir static\img
if not exist static\css mkdir static\css
if not exist static\js mkdir static\js

echo Criando placeholder para o logo se não existir...
if not exist static\img\logo.png (
    echo ^<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"^>^<circle cx="50" cy="50" r="40" stroke="black" stroke-width="3" fill="orange" /^>^<text x="50" y="55" font-family="Arial" font-size="14" text-anchor="middle" fill="white"^>LOGO^</text^>^</svg^> > static\img\logo.svg
    echo ATENÇÃO: Substitua o arquivo logo.svg pelo logo.png real antes de distribuir!
)

echo Criando hook para Office365...
echo # hooks/hook-office365.py > hooks\hook-office365.py
echo from PyInstaller.utils.hooks import collect_submodules >> hooks\hook-office365.py
echo. >> hooks\hook-office365.py
echo hiddenimports = collect_submodules('office365') >> hooks\hook-office365.py

echo Gerando o executável com PyInstaller...
pyinstaller --clean matching_system.spec

echo Build concluído! O executável está em dist\MatchingSystem\

pause