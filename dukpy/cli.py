# -*- coding: utf-8 -*-
import argparse
import sys

import dukpy


def main():
    parser = argparse.ArgumentParser(description="Run a javascript script")
    parser.add_argument("filename", help="path of the script to run")
    args = parser.parse_args(sys.argv[1:])

    dukpy.run(args.filename)
