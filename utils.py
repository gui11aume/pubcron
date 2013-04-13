# -*- coding:utf-8 -*-

import os
import json
import zlib

import jinja2


# Globals.
BASE_DIR = os.path.dirname(__file__)
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
JINJA_ENV = jinja2.Environment(
          loader=jinja2.FileSystemLoader(TEMPLATE_DIR))

def render(template_name, template_vals={}):
   template = JINJA_ENV.get_template(template_name)
   return template.render(template_vals)


def decrypt(entity, field):
   """Convenience function to extract compressed attributes."""
   return json.loads(zlib.decompress(getattr(entity, field)))
