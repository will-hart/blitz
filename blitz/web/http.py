__author__ = 'Will Hart'

import os
from tornado.web import RequestHandler


class IndexHandler(RequestHandler):

    def get(self):
        # just read the file in to prevent tornado from processing handlebars
        resp_file = open(os.path.join(self.application.settings['template_path'], "index.html"))
        self.write(resp_file.read())
