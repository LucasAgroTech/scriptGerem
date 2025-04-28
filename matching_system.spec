# -*- mode: python ; coding: utf-8 -*-
block_cipher = None
added_files = [
    ('templates', 'templates'),
    ('.env', '.'),
    ('office365_api', 'office365_api'),
    ('uploads', 'uploads'),
    ('downloads', 'downloads'),
    ('static', 'static'),  # Adicionando arquivos estáticos
]

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'office365.sharepoint.client_context',
        'office365.runtime.auth.user_credential',
        'office365.sharepoint.files.file',
        'pandas',
        'openpyxl',
        'io',
        'json',
        'numpy'
    ],
    hookspath=['hooks'],  # Adicionando pasta de hooks
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MatchingSystem',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='static/img/favicon.ico'  # Adicionando ícone para o executável
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MatchingSystem',
)