import py2exe

py2exe.freeze(
      options={'compressed': 1, 'optimize': 2, 'bundle_files': 0},
      windows=[{'script': "battery.py"}],
      data_files=[
            ('.', ['.venv\Lib\site-packages\libusb_package\libusb-1.0.dll'])
      ],
      zipfile=None,
)
