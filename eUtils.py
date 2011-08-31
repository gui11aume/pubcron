import sys
import urllib
import urllib2
import datetime as dt

from xml.dom import minidom

## CONSTANTS ##
BASE = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
RETMAX = 5000

# Convenience XML extraction functions.
def unlist_or_raise(nodelist):
   if len(nodelist) > 1:
      raise Exception("more than one element in %s" % nodelist)
   return nodelist[0] 

def _nodes(node, tag):
   return node.getElementsByTagName(tag)

def _node(node, tag):
   return unlist_or_raise(_nodes(node, tag))

def _data(node, tag):
   extract = unlist_or_raise(_nodes(node, tag))
   return extract.firstChild.data

def _child_of(node, tag):
   for child in _nodes(node, tag):
      if child.parentNode is node: return child



##########################################
######          Exceptions          ######
##########################################

# eSearch Exceptions.
class eSearchException(Exception):
   def __init__(self, value):
      self.value = value

class PubMedError(eSearchException):
   def __str__(self):
      return self.value.toxml()

class RetMaxExceeded(eSearchException):
   def __str__(self):
      return "count %d > RETMAX = %d" % (self.value, RETMAX)

class NoHitException(eSearchException):
   def __str__(self):
      return self.value.toxml()

# XML Exceptions.
class XMLException(Exception):
   pass

class NodeNotFoundException(XMLException):
   def __init__(self, xmldoc, tag_name, top):
      self.xmldoc = xmldoc
      self.tag_name = tag_name
      self.top = top

   def __str__(self):
      return """
      %s
      tag_name=%s""" % (self.xmldoc.toxml(), self.tag_name)



##########################################
######           XMLabstr           ######
##########################################

class XMLabstr:
   """Representation of a PubMed Abstract parsed by minidom."""
   def __init__(self, abstr):
      self.abstr = abstr

      # PubMed ID and DOI.
      self.pmid = _child_of(_node(abstr, "MedlineCitation"), \
            "PMID").firstChild.data
      try:
         self.doi = [node.firstChild.data for node in _nodes(abstr, "ArticleId") \
            if node.attributes["IdType"].value == "doi"].pop()
      except Exception: #TODO: which!!!
         self.doi = None

      # Article Language.
      self.language = _data(abstr, "Language")

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

      # Publication date as datetime object and string.
      # Extract year and month.
      datestr = "".join([_data(_node(abstr, "PubDate"), ym) 
            for ym in ("Year", "Month")])
      # Extract day if available.
      try:
         datestr += _data(_node(abstr, "PubDate"), "Day")
         self.day = True
      except Exception: #TODO: WHICH EXCEPTION???
         datestr += "01"
         self.day = False
      self.pubdate = dt.datetime.strptime(datestr, "%Y%b%d")
      if self.day:
         self.format_pubdate("%B %d, %Y")
      else:
         self.format_pubdate("%B, %Y")

      # Article Title and abstract text.
      self.title = _data(abstr, "ArticleTitle")
      try:
         self.body = _data(abstr, "AbstractText")
      except Exception:
         self.body = "No abstract available."

   def format_pubdate(self, fmt):
      self.fmt_pubdate = self.pubdate.strftime(fmt)
  


##########################################
######           Functions          ######
##########################################

def cron_query(term, date_from=None, date_to=None):
   """Cron wrapper allowing to perform a request with the same term
   at different dates. Return a list of XMLabstr objects."""
   date_from = date_from if date_from else \
         dt.datetime.today() + dt.timedelta(-1)
   date_to = date_to if date_to else date_from
   #term += date_from.strftime("%Y/%m/%d:") + \
   term = "filion+gj[author]"
   ablist = []
   for xml in _nodes(minidom.parseString(query_abstracts(term)), \
         "PubmedArticle"):
         ablist.append(XMLabstr(xml))
   return ablist


def query_abstracts(term):
   """Query PubMed with term and return results in XML (text) format."""
   try:
      xmldoc = robust_eSearch_query(term)
   except NoHitException:
      return
   return eFetch_query(
         key = _child_of(_node(xmldoc, "eSearchResult"), \
               "QueryKey").firstChild.data,
         webenv = _child_of(_node(xmldoc, "eSearchResult"), \
               "WebEnv").firstChild.data)


def robust_eSearch_query(term):
   """Robust eSearch query in two steps: the first request checks
   for errors and counts the hits, the second returns the results
   using "usehistory=y". Fails if errors are encountered, or if no
   result."""
   # Initial query to check for errors and get hit count.
   xmldoc = minidom.parseString(
         eSearch_query(term=term, usehistory=False, retmax=0))
   # Check for PubMedErrors. Return the xml result for diagnostic in
   # case of ErrorList tag.
   if _nodes(xmldoc, "ErrorList"):
      raise PubMedError(xmldoc)

   count = int(_child_of(_node(xmldoc, "eSearchResult"), \
         "Count").firstChild.data)
   if count > RETMAX:
      raise RetMaxExceeded(count)

   if count == 0:
      raise NoHitException(xmldoc)

   return minidom.parseString(
         eSearch_query(term=term, usehistory=True, retmax=count))


def eSearch_query(term, usehistory=False, retmax=0):
   """Basic error-prone eSearch query."""
   usehistory = "&usehistory=y" if usehistory else ""
   return urllib2.urlopen(BASE + "esearch.fcgi?db=pubmed" \
        + "&term=" + term \
        + usehistory \
        + "&retmax=" + str(retmax)).read()


def eFetch_query(key, webenv):
   """Basic eFetch query through QueryKey and WebEnv."""
   return urllib2.urlopen(BASE + "efetch.fcgi?db=pubmed" \
         + "&query_key=" + key \
         + "&WebEnv=" + webenv \
         + "&retmode=xml").read()
