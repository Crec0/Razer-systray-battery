import py2exe

py2exe.freeze(
      options={'compressed': 1, 'optimize': 2, 'bundle_files': 0},
      windows=[{'script': "battery.py"}],
      zipfile=None,
)
