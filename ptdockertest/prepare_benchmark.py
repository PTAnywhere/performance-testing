"""
Created on 22/09/2015
@author: Aitor Gomez Goiri <aitor.gomez-goiri@open.ac.uk>
Script to create database.
"""

from argparse import ArgumentParser
from models import PerformanceTestDAO, Test



def main(database_file):
    dao = PerformanceTestDAO(database_file)
    session = dao.create_session()
    for num_containers in (1, 5, 10, 20, 40, 60, 80, 100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600):
        test = Test(image_id='packettracer_xvfb_mount', volumes='/opt/pt:/opt/pt:ro', number_of_containers=num_containers, repetitions=1)
        session.add(test)
    session.commit()

def entry_point():
    parser = ArgumentParser(description='Create database and create data for the benchmark.')
    parser.add_argument('-db', default='/tmp/benchmark.db', dest='database', help='Database file.')
    args = parser.parse_args()
    main(args.database)


if __name__ == "__main__":
    entry_point()
