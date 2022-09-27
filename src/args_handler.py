import getopt
import logging

from config import engine_settings


def print_usage():
    usage = """\
Usage: python main.py [OPTIONS] [INPUT]
If INPUT is a directory, all files (including subdirectories) in it will be optimized.

Options:
  -h            Display this help message and exit
  -o OUTPUT     Optimized output dockerfile path, default to INPUT + SUFFIX
                (SUFFIX is ".optimized" by default, so this will be "INPUT.optimized" by default)
                If INPUT is a directory, then OUTPUT should be a directory too
  -s SUFFIX     Set the prefix of the output file, default to ".optimized"
                If INPUT and OUTPUT both are directories, then SUFFIX will be ignored
  -S            Show the statistics of optimizations
  -f FAIL_FILE  Output all dockerfiles that are failed to optimize into FAIL_FILE
                FAIL_FILE is './DPMO_failures.txt' by default
  -w            Only display warning and error messages
"""
    print(usage)


def init_by_argv(argv):
    """
    Parse the command-line arguments, and then set the engine settings (in config.py).

    :param argv: command-line arguments (sys.argv[1:])
    :return: None
    """
    try:
        opts, args = getopt.getopt(argv, 'ho:s:Sf:w')
    except getopt.GetoptError as e:
        logging.error('Invalid option: "{0}"'.format(e.opt))
        exit(-1)
        return
    if len(opts) > 0 and opts[0][0] == '-h':
        print_usage()
        exit(0)
        return
    if len(args) == 0:
        logging.error('Input path is empty!')
        exit(-1)
        return

    engine_settings.input_file = args[0]

    for option, value in opts:
        if option == '-o':
            engine_settings.output_file = value
        elif option == '-s':
            engine_settings.suffix = value
        elif option == '-S':
            engine_settings.show_stats = True
        elif option == '-f':
            engine_settings.fail_file = value
        elif option == '-w':
            engine_settings.logging_level = logging.WARNING

    try:
        engine_settings.fail_fileobj = open(file=engine_settings.fail_file, mode='w')
    except Exception as e:  # Including: IOError
        logging.error(e)
        exit(-1)
        return

    logging.basicConfig(
        format='[%(asctime)s %(levelname)s %(name)s]: %(message)s',
        level=engine_settings.logging_level
    )
