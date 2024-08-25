import py2exe

py2exe.freeze(
      options={'compressed': 1, 'optimize': 1, 'bundle_files': 0},
      console=[{'script': "battery.py"}],
      zipfile=None,
)
