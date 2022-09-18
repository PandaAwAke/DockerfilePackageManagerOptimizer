class GlobalStatus(object):
    def __init__(self, work_dir='/', user='root', user_dirs=None):
        if user_dirs is None:
            user_dirs = {'root': '/root/'}   # dir is always ends with '/'
        self.work_dir = work_dir
        self.user = user
        self.user_dirs = user_dirs

    def __eq__(self, other):
        return self.work_dir == other.work_dir and \
            self.user == other.user and \
            self.user_dirs == other.user_dirs
