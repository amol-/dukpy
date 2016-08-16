# -*- coding: utf-8 -*-
import argparse
import sys
from .nodelike import NodeLikeInterpreter


def main():
    parser = argparse.ArgumentParser(description='Run a javascript script')
    parser.add_argument('filename', help='path of the script to run')
    args = parser.parse_args(sys.argv[1:])

    with open(args.filename) as f:
        sourcecode = f.read()

        if sourcecode.startswith('#!'):
            # Remove shebang
            _, sourcecode = sourcecode.split('\n', 1)
            sourcecode = '\n' + sourcecode

        runner = NodeLikeInterpreter()
        runner.evaljs(sourcecode)