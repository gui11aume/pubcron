# -*- coding: utf-8 -*-

import eUtils
import datetime

term = "english[Language]+AND+Journal article[Publication Type]" +\
      "+AND+(Science[Journal]+OR+Nature[Journal]+OR+Cell[Journal])"+\
      "[""]"

def query():
   return eUtils.cron_query(term=term)
