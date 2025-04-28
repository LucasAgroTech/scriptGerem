@echo off
echo ===== Preparando arquivos estáticos para o Matching System =====

echo Criando estrutura de diretórios...
if not exist static mkdir static
if not exist static\img mkdir static\img
if not exist static\css mkdir static\css
if not exist static\js mkdir static\js

echo Criando placeholder para o logo...
echo ^<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"^>^<circle cx="50" cy="50" r="40" stroke="black" stroke-width="3" fill="orange" /^>^<text x="50" y="55" font-family="Arial" font-size="14" text-anchor="middle" fill="white"^>LOGO^</text^>^</svg^> > static\img\logo.svg

echo Convertendo SVG para ICO (placeholder)...
echo Nota: Substitua estes arquivos pelos reais antes do build final

echo ^<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"^>^<circle cx="16" cy="16" r="14" stroke="black" stroke-width="1" fill="orange" /^>^</svg^> > static\img\favicon.svg

echo Criando placeholder para o CSS...
echo /* Stylesheet principal */ > static\css\main.css

echo Criando placeholder para o JavaScript...
echo // Script principal > static\js\main.js

echo.
echo ===== Preparação de arquivos estáticos concluída =====
echo Substitua os arquivos placeholder pelos arquivos reais antes do build final
echo.

pause