# -*- coding: utf-8 -*-

import sys
import urllib
import urllib2
import datetime as dt

from xml.dom import minidom

## CONSTANTS ##
BASE = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
RETMAX = 5000

# Convenience XML extraction functions.
def _unlist_or_raise(nodelist, tag):
   if len(nodelist) > 1:
      raise MultipleTagsException(tag)
   try:
      return nodelist[0]
   except IndexError:
      return u""

def _nodes(node, tag):
   return node.getElementsByTagName(tag)

def _node(node, tag):
   return _unlist_or_raise(_nodes(node, tag), tag)

def _data(node, tag):
   extract = _unlist_or_raise(_nodes(node, tag), tag)
   return extract.firstChild.data if extract else u""

def _child_of(node, tag):
   for child in _nodes(node, tag):
      if child.parentNode is node: return child



##########################################
######          Exceptions          ######
##########################################

# eSearch Exceptions.
class eSearchException(Exception):
   pass

class RetMaxExceeded(eSearchException):
   pass

class NoHitException(eSearchException):
   pass

class PubMedException(eSearchException):
   def __init__(self, pair_list):
      class ErrorPair:
         pass
      self.pair_list = []
      for pair in pair_list:
         o = ErrorPair()
         o.term = str(pair[0])
         o.message = str(pair[1])
         self.pair_list.append(o)


   def __str__(self):
      return str(self.pair_list)

# XML Exceptions.
class XMLException(Exception):
   pass

class MultipleTagsException(XMLException):
   pass


##########################################
######           XMLabstr           ######
##########################################

class XMLabstr:
   """Representation of a PubMed Abstract parsed by minidom.
   Only implements a constructor that specifies static attributes
   for easier use in Django templates."""

   def __init__(self, abstr):
      self.abstr = abstr

      # PubMed ID.
      self.pmid = _child_of(_node(abstr, "MedlineCitation"), \
            "PMID").firstChild.data

      # Article Languages.
      self.languages = _nodes(abstr, "Language")

      # Journal and publication types.
      self.journal = _data(_node(abstr, "Journal"), "Title")
      self.pubtypes = [node.firstChild.data for node in \
           _nodes(abstr, "PublicationType")]

      # Authors.
      self.authors = ", ".join([_data(auth, "ForeName") + " " + \
            _data(auth, "LastName") for auth in _nodes(abstr, "Author")])
      self.initials = ", ".join([_data(auth, "Initials") + " " + \
            _data(auth, "LastName") for auth in _nodes(abstr, "Author")])

      # MeSH terms.
      self.majorMeSH = [node.firstChild.data for node in \
            _nodes(abstr, "DescriptorName") if \
            node.attributes["MajorTopicYN"].value == "Y"]
      self.minorMeSH = [node.firstChild.data for node in \
            _nodes(abstr, "DescriptorName") if \
            node.attributes["MajorTopicYN"].value == "N"]

      # Publication date as a string.
      self.pubdate = " ".join([_data(_node(abstr, "PubDate"), mdy) \
            for mdy in ("Month", "Day", "Year")])

      # Article Title and abstract text.
      self.title = _data(abstr, "ArticleTitle")
      self.body = " ".join([x.firstChild.data for x in \
            _nodes(abstr, "AbstractText")])



##########################################
######           Functions          ######
##########################################

def cron_query(term, date_from, date_to):
   """Cron wrapper allowing to perform a request with the same term
   at different dates. Return a list of XMLabstr objects."""
   # Update term with creation date information.
   term = "("+term+")" + date_from.strftime("+AND+(%Y%%2F%m%%2F%d:") + \
   date_to.strftime("%Y%%2F%m%%2F%d[crdt])")

   hits = fails = []
   for xml_node in _nodes(minidom.parseString(fetch_abstracts(term)), \
         "PubmedArticle"):
      try:
         abstr = XMLabstr(xml_node)
      except Exception:
         # Collect fails (for diagnostic).
         fails.append(xml_node)
      else:
         hits.append(abstr)
   return (hits, fails)


def fetch_abstracts(term):
   """Query PubMed and return PubmedArticleSet in (non parsed)
   XMLformat, or None if no hit."""
   xmldoc = robust_eSearch_query(term)
   return eFetch_query(
         key = _child_of(_node(xmldoc, "eSearchResult"), \
               "QueryKey").firstChild.data,
         webenv = _child_of(_node(xmldoc, "eSearchResult"), \
               "WebEnv").firstChild.data)


def eFetch_query(key, webenv):
   """Basic eFetch query through QueryKey and WebEnv."""
   return urllib2.urlopen(BASE + "efetch.fcgi?db=pubmed" \
         + "&query_key=" + key \
         + "&WebEnv=" + webenv \
         + "&retmode=xml").read()


def robust_eSearch_query(term):
   """Robust eSearch query is carried out in two steps: the first
   request returns hit count and meta information (PubMed query
   translation, errors, warnings etc.) on which error checking
   is performed. The second request returns results using
   "usehistory=y", producing QueryKey and WebEnv output fields that
   can be used for future requests or passed on to eFetch."""
   # Initial query to check for errors and get hit count.
   xmldoc = minidom.parseString(eSearch_query(term=term,
         usehistory=False, retmax=0))
   # Check for PubMedExceptions. Return the xml result for diagnostic in
   # case of ErrorList tag.
   if _nodes(xmldoc, "ErrorList"):
      translation = _data(xmldoc, "QueryTranslation")
      report = [(u"Term (as queried)", term.encode('utf-8')), \
            (u"QueryTranslation", translation)]
      errors = _node(xmldoc, "ErrorList").childNodes
      report += [(nd.nodeName, nd.firstChild.data) for nd in errors]
      raise PubMedException(report)

   # Get and control hit count.
   count = int(_child_of(_node(xmldoc, "eSearchResult"), \
         "Count").firstChild.data)
   if count > RETMAX:
      raise RetMaxExceeded(count)
   if count == 0:
      raise NoHitException(term)

   return minidom.parseString(eSearch_query(term=term,
         usehistory=True, retmax=count))


def eSearch_query(term, usehistory=False, retmax=0):
   """Basic error-prone eSearch query."""
   usehistory = "&usehistory=y" if usehistory else ""
   return urllib2.urlopen(BASE + "esearch.fcgi?db=pubmed" \
        + "&term=" + term \
        + usehistory \
        + "&retmax=" + str(retmax)).read()
