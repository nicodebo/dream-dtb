"""
Dream note gui
"""
from setuptools import find_packages, setup

dependencies = ['click', 'neovim', 'SQLAlchemy', 'sqlalchemy-utils']

setup(
    name='dream-dtb',
    version='0.1.0',
    url='https://github.com/nicodebo/dream-dtb',
    license='BSD',
    author='Nicolas D.',
    author_email='nico.debo@openmailbox.org',
    description='Dream note gui ',
    keywords='nvim, neovim, gui, dream',
    long_description=open('README.rst').read(),
    use_scm_version=True,
    packages=find_packages(exclude=['tests']),
    python_requires='>=3.6',
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    setup_requires=['setuptools_scm'],
    install_requires=dependencies,
    entry_points={
        'console_scripts': [
            'dreamdtb = dream_dtb.cli:main',
        ],
    },
    classifiers=[
        # As from http://pypi.python.org/pypi?%3Aaction=list_classifiers
        # 'Development Status :: 1 - Planning',
        # 'Development Status :: 2 - Pre-Alpha',
        # 'Development Status :: 3 - Alpha',
        'Development Status :: 4 - Beta',
        # 'Development Status :: 5 - Production/Stable',
        # 'Development Status :: 6 - Mature',
        # 'Development Status :: 7 - Inactive',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX',
        'Operating System :: MacOS',
        'Operating System :: Unix',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ]
)
