from config.engine_config import engine_settings


class Stats(object):
    """
    The statistics of the optimization process.
    """

    def __init__(self):
        self.add_cache_num = 0
        self.insert_before_num = 0
        self.remove_command_num = 0
        self.remove_option_num = 0
        self.syntax_change_num = 0

        self.total_add_cache_num = 0
        self.total_insert_before_num = 0
        self.total_remove_command_num = 0
        self.total_remove_option_num = 0
        self.total_syntax_change_num = 0

        self.total_successful_files = 0
        self.total_failed_files = 0
        self.total_unchanged_files = 0

        self.total_optimization_dict = {}

    def one_file_optimization_num(self):
        return self.add_cache_num + self.insert_before_num \
               + self.remove_command_num + self.remove_option_num \
               + self.syntax_change_num

    def total_file_optimization_num(self):
        return self.total_add_cache_num + self.total_insert_before_num \
               + self.total_remove_command_num + self.total_remove_option_num \
               + self.total_syntax_change_num

    def total_files(self):
        return self.total_successful_files + self.total_failed_files + self.total_unchanged_files

    def one_file_str(self) -> str:
        """
        Return the statistics string of the optimization of one file.

        :return: the statistics string of the optimization of one file.
        """

        return 'Number of modifications of this dockerfile: {0}\n' \
               ' - Added --mount=type=cache: {1}\n' \
               ' - Inserted commands: {2}\n' \
               ' - Removed anti-cache commands: {3}\n' \
               ' - Removed anti-cache command options: {4}' \
               ' - Added/Modified syntax settings: {5}\n' \
            .format(self.one_file_optimization_num(),
                    self.add_cache_num,
                    self.insert_before_num,
                    self.remove_command_num,
                    self.remove_option_num,
                    self.syntax_change_num)

    def total_str(self) -> str:
        """
        Return the statistics string of the optimization of all files.

        :return: the statistics string of the optimization of all files.
        """

        return \
            '\n' \
            '-----------------[Statistics]-----------------\n' \
            ' - Total number of modifications: {}\n' \
            '   - Added --mount=type=cache: {}\n' \
            '   - Inserted commands: {}\n' \
            '   - Removed anti-cache commands: {}\n' \
            '   - Removed anti-cache command options: {}\n' \
            '   - Added/Modified syntax settings: {}\n' \
            '----------------------------------------------\n' \
            ' - Total files: {}\n' \
            '   - Successfully optimized files: {}\n' \
            '   - Failed files: {}\n' \
            '   - Unchanged files: {}\n' \
            ' - Optimization (Success) rate: {}%\n' \
            '----------------------------------------------\n' \
            ' - Optimization counts of Dockerfiles:\n' \
            '{}\n' \
            .format(self.total_file_optimization_num(),
                    self.total_add_cache_num,
                    self.total_insert_before_num,
                    self.total_remove_command_num,
                    self.total_remove_option_num,
                    self.total_syntax_change_num,

                    self.total_files(),
                    self.total_successful_files,
                    self.total_failed_files,
                    self.total_unchanged_files,
                    round(self.total_successful_files / self.total_files() * 100, 2),

                    self.optimization_dict_str()
                    )

    def optimization_dict_str(self) -> str:
        sorted_dict_items = sorted(self.total_optimization_dict.items(), key=lambda x: len(x[1]), reverse=True)
        lines = ''
        for stat_tuple, filenames in sorted_dict_items:
            count = len(filenames)
            lines += ' {},\t(Total: {}\t\tAddCache: {}\t\tInsertBefore: {}\t\tRemoveCommand: {}' \
                     '\tRemoveOption: {}\t\tSyntaxChange: {}) \n'\
                .format(
                    count,
                    sum(stat_tuple), stat_tuple[0], stat_tuple[1], stat_tuple[2], stat_tuple[3], stat_tuple[4]
                )
        return lines

    def optimization_dict_write_stat_file(self):
        s = '\n' \
            '-----------------[Statistics]-----------------\n' \
            ' - Total number of modifications: {}\n' \
            '   - Added --mount=type=cache: {}\n' \
            '   - Inserted commands: {}\n' \
            '   - Removed anti-cache commands: {}\n' \
            '   - Removed anti-cache command options: {}\n' \
            '   - Added/Modified syntax settings: {}\n' \
            '----------------------------------------------\n' \
            ' - Total files: {}\n' \
            '   - Successfully optimized files: {}\n' \
            '   - Failed files: {}\n' \
            '   - Unchanged files: {}\n' \
            ' - Optimization (Success) rate: {}%\n' \
            '----------------------------------------------\n' \
            ' - Optimization counts of Dockerfiles:\n' \
            .format(self.total_file_optimization_num(),
                    self.total_add_cache_num,
                    self.total_insert_before_num,
                    self.total_remove_command_num,
                    self.total_remove_option_num,
                    self.total_syntax_change_num,

                    self.total_files(),
                    self.total_successful_files,
                    self.total_failed_files,
                    self.total_unchanged_files,
                    round(self.total_successful_files / self.total_files() * 100, 2),
                    )
        engine_settings.stat_fileobj.writelines(s)
        engine_settings.stat_fileobj.flush()

        sorted_dict_items = sorted(self.total_optimization_dict.items(), key=lambda x: len(x[1]), reverse=True)
        for stat_tuple, filenames in sorted_dict_items:
            lines = []
            count = len(filenames)
            lines.append(
                '{},\t(Total: {}\t\tAddCache: {}\t\tInsertBefore: {}\t\tRemoveCommand: {}'
                '\tRemoveOption: {}\t\tSyntaxChange: {})\n'.format(
                    count, sum(stat_tuple), stat_tuple[0], stat_tuple[1], stat_tuple[2], stat_tuple[3], stat_tuple[4]
                ))
            for filename in filenames:
                lines.append(filename + '\n')
            engine_settings.stat_fileobj.writelines(lines)
            engine_settings.stat_fileobj.flush()

    def finished_one_file(self, filename):
        """
        Clear the statistics of one file.

        :return:
        """
        this_file = (
            self.add_cache_num,
            self.insert_before_num,
            self.remove_command_num,
            self.remove_option_num,
            self.syntax_change_num
        )
        if self.add_cache_num > 0:
            if self.total_optimization_dict.get(this_file):
                self.total_optimization_dict[this_file].append(filename)
            else:
                self.total_optimization_dict[this_file] = [filename]

        self.add_cache_num = 0
        self.insert_before_num = 0
        self.remove_command_num = 0
        self.remove_option_num = 0
        self.syntax_change_num = 0

    def clear_total(self):
        """
        Clear the statistics of all files.

        :return:
        """
        self.total_add_cache_num = 0
        self.total_insert_before_num = 0
        self.total_remove_command_num = 0
        self.total_remove_option_num = 0
        self.total_syntax_change_num = 0

        self.total_successful_files = 0
        self.total_failed_files = 0
        self.total_unchanged_files = 0

    def add_cache(self):
        self.add_cache_num += 1
        self.total_add_cache_num += 1

    def insert_before(self):
        self.insert_before_num += 1
        self.total_insert_before_num += 1

    def remove_command(self):
        self.remove_command_num += 1
        self.total_remove_command_num += 1

    def remove_option(self):
        self.remove_option_num += 1
        self.total_remove_option_num += 1

    def syntax_change(self):
        self.syntax_change_num += 1
        self.total_syntax_change_num += 1

    def successful_one_file(self):
        self.total_successful_files += 1

    def failed_one_file(self):
        self.total_failed_files += 1

    def unchanged_one_file(self):
        self.total_unchanged_files += 1


stats = Stats()
