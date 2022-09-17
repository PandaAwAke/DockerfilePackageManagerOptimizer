class Stats(object):
    def __init__(self):
        self.add_cache_num = 0
        self.insert_before_num = 0
        self.syntax_change = 0

    def __str__(self):
        return 'Total number of modification: {0}\n' \
               ' - Added --mount=type=cache: {1}\n' \
               ' - Inserted commands: {2}\n' \
               ' - Added/Modified syntax settings: {3}\n'\
            .format(self.add_cache_num + self.insert_before_num + self.syntax_change,
                    self.add_cache_num,
                    self.insert_before_num,
                    self.syntax_change)

stats = Stats()
