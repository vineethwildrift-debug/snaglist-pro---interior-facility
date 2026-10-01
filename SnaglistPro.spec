# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app_launcher.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('snaglist_pro/web/templates', 'snaglist_pro/web/templates'),
        ('snaglist_pro/web/static', 'snaglist_pro/web/static'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch', 'torchvision', 'tensorflow', 'transformers', 'sklearn', 'scipy',
        'pandas', 'matplotlib', 'cv2', 'onnxruntime', 'pytest', 'IPython',
        'sqlalchemy', 'zmq', 'jedi', 'parso', 'notebook', 'nbformat',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SnaglistPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='file_version_info.txt',
)
