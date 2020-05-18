from setuptools import setup

# reading long description from file
with open('README.md') as file:
    long_description = file.read()


# specify requirements of your package here
REQUIREMENTS = []

# some more details
CLASSIFIERS = [
  "Programming Language :: Python :: 3",
  "Programming Language :: Python :: 3.7",
    "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    "Operating System :: OS Independent"
 ]

# calling the setup function
setup(name='abmatt',
      version='0.1.0',
      description='Brres file material editor',
      long_description=long_description,
      long_description_content_type="text/markdown",
      url='https://github.com/Robert-N7/abmatt',
      author='Robert Nelson',
      author_email='robert7.nelson@gmail.com',
      license='GPLv3',
      packages=setuptools.find_packages(),
      classifiers=CLASSIFIERS,
      install_requires=REQUIREMENTS,
      keywords='Mario Kart Wii Brres Material MDL0'
      )