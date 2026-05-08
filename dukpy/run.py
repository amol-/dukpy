# -*- coding: utf-8 -*-
import argparse
import sys
from .nodelike import NodeLikeInterpreter


def main():
    parser = argparse.ArgumentParser(description="Run a javascript script")
    parser.add_argument("filename", help="path of the script to run")
    args = parser.parse_args(sys.argv[1:])

    with open(args.filename, encoding="utf-8") as f:
        sourcecode = f.read()

        # This is the CLI's only host-owned source text adaptation: QuickJS owns
        # JavaScript parsing, while POSIX shebangs are host launch metadata. Keep
        # a blank first line so QuickJS syntax and stack line numbers still match
        # the script file without scanning the rest of the source.
        if sourcecode.startswith("#!"):
            _, separator, sourcecode = sourcecode.partition("\n")
            sourcecode = "\n" + sourcecode if separator else "\n"

        runner = NodeLikeInterpreter()
        runner.evaljs(sourcecode)
