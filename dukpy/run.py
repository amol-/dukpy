from .coffee import coffee_compile
from .tsc import typescript_compile
from .babel import babel_compile
from .babel import jsx_compile
from .lessc import less_compile

import argparse
import sys

def main():

    parser = argparse.ArgumentParser(description='Compile a file to JavaScript or CSS')

    parser.add_argument('lang', help='Language of the file to compile')
    parser.add_argument('input', nargs='?', help='Path of the input file')
    parser.add_argument('output', nargs='?', help='Path of the output file')

    args = parser.parse_args(sys.argv[1:])

    lang = args.lang.lower().strip() if args.lang else None
    input = args.input.strip() if args.input else None
    output = args.output.strip() if args.output else None

    try:

        with open(input, "r") as input_file:

            input_code = input_file.read()

            if input_code.startswith("#!"):

                _, input_code = input_code.split("\n", 1)
                input_code = "\n" + input_code

        try:

            if lang == "coffee" or lang == "coffeescript":

                output_code = coffee_compile(input_code)

            elif lang == "ts" or lang == "typescript":

                output_code = typescript_compile(input_code)

            elif lang == "babel" or lang == "babeljs":

                output_code = babel_compile(input_code)

            elif lang == "jsx":

                output_code = jsx_compile(input_code)

            elif lang == "less":

                output_code = less_compile(input_code)

            else:

                print("Invalid language argument.")

                return

            try:

                with open(output, "w") as output_file:

                    output_file.write(str(output_code))

                print("Success!")

                return

            except:

                print("Error trying to write the output file.")

                return

        except:

            print("Error trying to compile the input file.")

            return

    except:

        print("Error trying to read the input file.")

        return
