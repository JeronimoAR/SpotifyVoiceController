from setuptools import setup, Extension

setup(
    name='PyAudio',
    version='0.2.11',
    description='Bindings for PortAudio v19',
    ext_modules=[
        Extension(
            'pyaudio._portaudio',
            sources=['src/pyaudio/device_api.c'],
            include_dirs=['/usr/include'],
            libraries=['portaudio']
        )
    ]
)