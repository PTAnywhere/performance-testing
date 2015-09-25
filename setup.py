"""
Created on September 22, 2015

@author: Aitor Gómez Goiri <aitor.gomez-goiri@open.ac.uk>

To install/reinstall/uninstall the project and its dependencies using pip:
     pip install ./
     pip install ./ --upgrade
     pip uninstall ptdockertest
"""
from setuptools import setup  # , find_packages

setup(name="ptdockertest",
      version="0.1",
      description="Project which measures the performance of the Docker-based Packet Tracer.",
      # long_description = "",
      author="Aitor Gomez-Goiri",
      author_email="aitor.gomez-goiri@open.ac.uk",
      maintainer="Aitor Gomez-Goiri",
      maintainer_email="aitor.gomez-goiri@open.ac.uk",
      url="https://github.com/PTAnywhere/performance-testing",
      # license = "http://www.apache.org/licenses/LICENSE-2.0",
      platforms=["any"],
      packages=["ptdockertest"],
      install_requires=["docker-py", "SQLAlchemy", "humanfriendly"],
      entry_points={
          "console_scripts": [
            "prepare-benchmark = ptdockertest.prepare_benchmark:entry_point",
            "run-benchmark = ptdockertest.run_benchmark:entry_point",
            "generate-plots = ptdockertest.generate_plots:entry_point",
          ],
      },
)
