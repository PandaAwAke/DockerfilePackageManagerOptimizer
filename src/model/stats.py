class Stats(object):
    """
    The statistics of the optimization process.
    """

    def __init__(self):
        self.add_cache_num = 0
        self.insert_before_num = 0
        self.syntax_change_num = 0
        self.remove_command_num = 0

        self.total_add_cache_num = 0
        self.total_insert_before_num = 0
        self.total_syntax_change_num = 0
        self.total_remove_command_num = 0

    def one_file_str(self):
        """
        Return the statistics string of the optimization of one file.

        :return: the statistics string of the optimization of one file.
        """

        return 'Number of modifications of this dockerfile: {0}\n' \
               ' - Added --mount=type=cache: {1}\n' \
               ' - Inserted commands: {2}\n' \
               ' - Removed anti-cache commands: {3}\n' \
               ' - Added/Modified syntax settings: {4}\n' \
            .format(self.add_cache_num + self.insert_before_num
                    + self.remove_command_num + self.syntax_change_num,
                    self.add_cache_num,
                    self.insert_before_num,
                    self.remove_command_num,
                    self.syntax_change_num)

    def total_str(self):
        """
        Return the statistics string of the optimization of all files.

        :return: the statistics string of the optimization of all files.
        """

        return 'Total number of modifications: {0}\n' \
               ' - Added --mount=type=cache: {1}\n' \
               ' - Inserted commands: {2}\n' \
               ' - Removed anti-cache commands: {3}\n' \
               ' - Added/Modified syntax settings: {4}\n' \
            .format(self.total_add_cache_num + self.total_insert_before_num
                    + self.total_remove_command_num + self.total_syntax_change_num,
                    self.total_add_cache_num,
                    self.total_insert_before_num,
                    self.total_remove_command_num,
                    self.total_syntax_change_num)

    def clear_one_file(self):
        """
        Clear the statistics of one file.

        :return:
        """
        self.add_cache_num = 0
        self.insert_before_num = 0
        self.remove_command_num = 0
        self.syntax_change_num = 0

    def clear_total(self):
        """
        Clear the statistics of all files.

        :return:
        """
        self.clear_one_file()

        self.total_add_cache_num = 0
        self.total_insert_before_num = 0
        self.total_remove_command_num = 0
        self.total_syntax_change_num = 0

    def add_cache(self):
        self.add_cache_num += 1
        self.total_add_cache_num += 1

    def insert_before(self):
        self.insert_before_num += 1
        self.total_insert_before_num += 1

    def remove_command(self):
        self.remove_command_num += 1
        self.total_remove_command_num += 1

    def syntax_change(self):
        self.syntax_change_num += 1
        self.total_syntax_change_num += 1


stats = Stats()
