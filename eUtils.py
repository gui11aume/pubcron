# -*- coding: utf-8 -*-

import sys
import urllib
import urllib2

from SAXmed import eFetchResultHandler, eSearchResultHandler
from xml.sax import make_parser


##########################################
######          Constants           ######
##########################################

# Base link to eUtils.
BASE = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/"


##########################################
######          Exceptions          ######
##########################################

# eSearch/PubMed Exceptions.
class eSearchException(Exception):
   pass

class NoHitException(eSearchException):
   pass

class PubMedException(eSearchException):
   pass


##########################################
######           Functions          ######
##########################################


def fetch_Abstr(term, **kwargs):
   """Query PubMed and return a list of Abstr instances."""

   # Note: The memory usage is about 1 Mb per 100 PubMed abstracts.
   Abstr_list = []
   parser = make_parser()
   parser.setContentHandler(eFetchResultHandler(Abstr_list))
   parser.parse(fetch_XML(term, **kwargs))
   return Abstr_list


def fetch_ids(id_list, **kwargs):
   """Query PubMed with a list of ids and return a list of
   Abstr instances."""

   # Query 50 ids at a time (otherwise the URL is too long).
   n = len(id_list)
   id_chunks = [
       ','.join(id_list[i*50:(i+1)*50-1]) for i in range(1+(n-1)/50)
   ]

   Abstr_list = []
   parser = make_parser()
   parser.setContentHandler(eFetchResultHandler(Abstr_list))
   for id_chunk in id_chunks:
      parser.parse(eFetch_query(id=id_chunk))
   return Abstr_list


def fetch_XML(term, **kwargs):
   """Query PubMed and return an XML stream."""

   eFetch_params = kwargs
   parser = make_parser()
   parser.setContentHandler(eSearchResultHandler(eFetch_params))
   parser.parse(robust_eSearch_query(term, **kwargs))

   # Plug-in the results of eSearch in eFetch.
   return eFetch_query(**eFetch_params)


def eFetch_query(**kwargs):
   """Basic eFetch query through QueryKey and WebEnv.
   Return an XML stream."""

   extrargs = ''.join(['&%s=%s' % it for it in kwargs.items()])

   return urllib2.urlopen(BASE + "efetch.fcgi?db=pubmed" \
         + extrargs \
         + "&retmode=xml")


def robust_eSearch_query(term, retmax=float('inf'), **kwargs):
   """Robust eSearch query is carried out in two steps: the first
   request returns hit count and meta information (PubMed query
   translation, errors, warnings etc.) on which error checking
   is performed. The second request returns results using
   "usehistory=y", producing QueryKey and WebEnv output fields that
   can be used for future requests or passed on to eFetch."""

   # Initial query to check for errors and get hit count.
   initial_query = {}
   parser = make_parser()
   parser.setContentHandler(eSearchResultHandler(initial_query))
   parser.parse(eSearch_query(
         term = term,
         usehistory = False,
         retmax = 0,
         **kwargs
      ))
   # Check for the presence of "ErrorList".
   if initial_query.get('errors'):
      raise PubMedException(initial_query.get('errors'))

   # Check hit count.
   count = int(initial_query.get('count'))
   if count == 0:
      raise NoHitException(term)

   return eSearch_query(
         term = term,
         usehistory = True,
         retmax = min(count, retmax)
   )


def eSearch_query(term, usehistory=False, retmax=0, **kwargs):
   """Basic error-prone eSearch query."""

   usehistory = '&usehistory=y' if usehistory else ''
   extrargs = '&' + urllib.urlencode(kwargs) if kwargs else ''
   return urllib2.urlopen(BASE + "esearch.fcgi?db=pubmed" \
        + '&term=' + term \
        + usehistory \
        + '&retmax=' + str(retmax) \
        + extrargs
     )
