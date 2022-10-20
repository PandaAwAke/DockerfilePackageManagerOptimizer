"""
Copyright 2022 PandaAwAke

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import getopt
import logging
import os
import platform
import subprocess
import sys
import time

"""
A tool for testing whether a directory of dockerfiles can be built successfully (without build context).
"""


class Settings(object):
    """
    The settings of the tool.
    """

    def __init__(self):
        self.input_dir = None
        self.output_file = 'dockerfile_buildable.txt'
        self.timeout_file = 'dockerfile_buildable_timeout.txt'
        self.timeout = 300
        self.start_file = None
        self.input_files = None
        self.context = None


settings = Settings()


def _print_usage():
    usage = """\
Usage: python dockerfile_buildable.py [OPTIONS] [INPUT_DIR]

Options:
-o  OUTPUT_FILE     OUTPUT_FILE saves all successfully built dockerfiles.
                    Default to "dockerfile_buildable.txt".
-f  TIMEOUT_FILE    TIMEOUT_FILE saves all timeout-built dockerfiles.
                    Default to "dockerfile_buildable_timeout.txt".
-t  TIMEOUT         TIMEOUT specifies timeout seconds. Default to 300.
-s  START_FILE      Only dockerfiles after START_FILE in INPUT_DIR will be considered.
                    If provided, results will be appended to OUTPUT_FILE.
                    If this is empty, then all dockerfiles will be considered, and OUTPUT_FILE
                    will be truncated.
                    You should set this value when you run this tool for a second time to
                    continue the build testing. You can obtain this value from the output
                    message of the previous running.
-i  INPUT_FILES     Describe all dockerfiles which will be tested. Every line inside it should
                    be the filepath of a dockerfile. If specified, INPUT_DIR will be ignored.
-c  CONTEXT         Specify the build context. If not specified, context will be set to INPUT_DIR.

The name of built image will be set to "dpmo_test_dockerfiles:buildable".

Only a single dockerfile is considered, so the context of building doesn't matter.
"""
    print(usage)


def _handle_argv(argv):
    """
    Parse the command-line arguments, and then set the engine settings.

    :param argv: command-line arguments (sys.argv[1:])
    :return: None
    """
    try:
        opts, args = getopt.getopt(argv, 'o:f:t:s:i:c:')
    except getopt.GetoptError as e:
        logging.error('Invalid option: "{0}"'.format(e.opt))
        exit(-1)
        return
    if len(args) == 0:
        logging.error('Input path is empty!')
        exit(-1)
        return

    settings.input_dir = args[0]

    for option, value in opts:
        if option == '-o':
            settings.output_file = value
        elif option == '-f':
            settings.timeout_file = value
        elif option == '-t':
            settings.timeout = int(value)
        elif option == '-s':
            settings.start_file = value
        elif option == '-i':
            settings.input_files = value
        elif option == '-c':
            settings.context = value


def _test_one_dockerfile(count, context_path, input_file, f_output, f_timeout_output, f_build_time_output, timeout):
    """
    Try to build a single dockerfile.

    :param count: the count of the input_file
    :param context_path: the build context path.
    :param input_file: the path of the dockerfile.
    :param f_output: the output file object for successful builds.
    :param f_timeout_output: the output file object for timeout builds.
    :param timeout: timeout seconds.
    :return:
    """
    start_time = time.time()

    logging.info('{} - Testing "{}"...'.format(count, input_file))
    command = [
        'docker', 'build',
        '-f', input_file,
        '-t', '{}:{}'.format(
            os.path.basename(input_file).replace('.Dockerfile', ''),
            str(round(time.time()))),
        context_path
    ]
    if platform.system() != 'Windows':
        command = ['DOCKER_BUILDKIT=1'] + command

    dev_null = open(os.devnull, 'w')
    proc = subprocess.Popen(command, stdout=dev_null, stderr=dev_null)
    try:
        status = proc.wait(timeout=timeout)
        if status == 0:
            end_time = time.time()
            logging.info('"{0}" is successfully built!'.format(input_file))
            f_output.write(input_file + '\n')
            f_build_time_output.write("{}\n".format(end_time - start_time))
        else:
            logging.info('"{0}" failed to built.'.format(input_file))
    except subprocess.TimeoutExpired as e:
        proc.kill()
        logging.info('"{0}" timed out.'.format(input_file))
        f_timeout_output.write(input_file + '\n')

    f_output.flush()
    f_timeout_output.flush()
    f_build_time_output.flush()


if __name__ == '__main__':
    argv = sys.argv
    if len(argv) < 2:
        _print_usage()
        exit(-1)

    _handle_argv(argv[1:])

    logging.basicConfig(
        format='[%(asctime)s %(levelname)s %(name)s]: %(message)s',
        level=logging.INFO
    )

    mode = 'w' if settings.start_file is None else 'a'
    start_testing = False
    start_time = time.time()

    if settings.context:
        context_path = settings.context
    else:
        context_path = settings.input_dir

    count = 0
    with open(settings.output_file, mode, encoding='utf-8') as f_output:
        with open(settings.timeout_file, mode, encoding='utf-8') as f_timeout_output:
            with open('build_success_times.txt', mode, encoding='utf-8') as f_build_time_output:
                if settings.input_files is None:
                    for current_dir, dirs, files in os.walk(settings.input_dir):
                        for f in files:
                            count += 1
                            input_file = os.path.join(current_dir, f)

                            if settings.start_file is None or input_file == settings.start_file.strip():
                                start_testing = True

                            if start_testing:
                                _test_one_dockerfile(
                                    count=count,
                                    context_path=context_path,
                                    input_file=input_file,
                                    f_output=f_output,
                                    f_timeout_output=f_timeout_output,
                                    f_build_time_output=f_build_time_output,
                                    timeout=settings.timeout
                                )

                else:
                    with open(settings.input_files, 'r', encoding='utf-8') as f_input_files:
                        line = f_input_files.readline()
                        while len(line) > 0:
                            count += 1
                            input_file = line.strip()

                            if settings.start_file is None or input_file == settings.start_file.strip():
                                start_testing = True

                            if start_testing:
                                _test_one_dockerfile(
                                    count=count,
                                    context_path=context_path,
                                    input_file=input_file,
                                    f_output=f_output,
                                    f_timeout_output=f_timeout_output,
                                    f_build_time_output=f_build_time_output,
                                    timeout=settings.timeout
                                )
                            line = f_input_files.readline()

    end_time = time.time()
    logging.warning("Seconds used: {}".format(end_time - start_time))
