import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'VERSION')) as f:
    VERSION = f.read()

README = open(os.path.join(here, 'README.md')).read()
CHANGES = open(os.path.join(here, 'CHANGES')).read()

requires = [
    'sqlalchemy==0.9.4',
    'psycopg2==2.6.1',
    'alembic==0.8.4',
]

tests_require = [
    'nose'
]

setup(name='pyramid-alembic',
      version=VERSION,
      description='Alembic bindings for pyramid',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
          "Programming Language :: Python",
          "Framework :: Pylons",
          ],
      author='Eduardo Santos',
      author_email='eduardo@eduardosan.com',
      url='https://github.com/eduardosan/pyramid-alembic',
      keywords='pyramid sqlalchemy alembic',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=tests_require,
      test_suite="pyramid_alembic",
      entry_points="""\
      """
      )
