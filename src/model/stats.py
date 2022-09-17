class Stats(object):
    def __init__(self):
        self.add_cache_num = 0
        self.insert_before_num = 0
        self.syntax_change_num = 0

        self.total_add_cache_num = 0
        self.total_insert_before_num = 0
        self.total_syntax_change_num = 0

    def __str__(self):
        return 'Number of modifications of this dockerfile: {0}\n' \
               ' - Added --mount=type=cache: {1}\n' \
               ' - Inserted commands: {2}\n' \
               ' - Added/Modified syntax settings: {3}\n' \
            .format(self.add_cache_num + self.insert_before_num + self.syntax_change_num,
                    self.add_cache_num,
                    self.insert_before_num,
                    self.syntax_change_num)

    def totalStr(self):
        return 'Total number of modifications: {0}\n' \
               ' - Added --mount=type=cache: {1}\n' \
               ' - Inserted commands: {2}\n' \
               ' - Added/Modified syntax settings: {3}\n' \
            .format(self.total_add_cache_num + self.total_insert_before_num + self.total_syntax_change_num,
                    self.total_add_cache_num,
                    self.total_insert_before_num,
                    self.total_syntax_change_num)

    def clear(self):
        self.add_cache_num = 0
        self.insert_before_num = 0
        self.syntax_change_num = 0

    def clear_total(self):
        self.clear()
        self.total_add_cache_num = 0
        self.total_insert_before_num = 0
        self.total_syntax_change_num = 0

    def add_cache(self):
        self.add_cache_num += 1
        self.total_add_cache_num += 1

    def insert_before(self):
        self.insert_before_num += 1
        self.total_insert_before_num += 1

    def syntax_change(self):
        self.syntax_change_num += 1
        self.total_syntax_change_num += 1


stats = Stats()
