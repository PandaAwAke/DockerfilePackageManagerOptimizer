import getopt
import logging

from config.engine_config import engine_settings


def print_usage():
    usage = """\
Usage: python main.py [OPTIONS] [INPUT]
If INPUT is a directory, all files (including subdirectories) in it will be optimized.
A logging file named 'DPMO.log' will be generated.

Options:
  -h            Display this help message and exit
  -o OUTPUT     Optimized output dockerfile path, default to INPUT + SUFFIX
                (SUFFIX is ".optimized" by default, so this will be "INPUT.optimized" by default)
                If INPUT is a directory, then OUTPUT should be a directory too
  -s SUFFIX     Set the prefix of the output file, default to ".optimized"
                If INPUT and OUTPUT both are directories, then SUFFIX will be ignored
  -S            Show optimization statistics for each file
  -f FAIL_FILE  Output all dockerfiles that are failed to optimize into FAIL_FILE
                FAIL_FILE is './DPMO_failures.txt' by default
  -w            Only show warning and error messages in the console
  -t            Substitute the commands to remove with true when optimizing. If not specified,
                DPMO will remove the command (and the connector after it if the connector exists)
                when optimizing.
"""
    print(usage)


def init_by_argv(argv):
    """
    Parse the command-line arguments, and then set the engine settings (in engine_config.py).

    :param argv: command-line arguments (sys.argv[1:])
    :return: None
    """
    try:
        opts, args = getopt.getopt(argv, 'ho:s:Sf:wt')
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
        elif option == '-t':
            engine_settings.remove_command_with_true = True

    try:
        engine_settings.fail_fileobj = open(file=engine_settings.fail_file, mode='w')
    except Exception as e:  # Including: IOError
        logging.error(e)
        exit(-1)
        return

    init_logger()


def init_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # formatter = logging.Formatter('[%(asctime)s - %(levelname)s - %(name)s]: %(message)s')
    formatter = logging.Formatter('[%(asctime)s - %(levelname)s]: %(message)s')

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(engine_settings.logging_level)

    file_handler = logging.FileHandler(filename='DPMO.log')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
