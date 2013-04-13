# -*- coding: utf-8 -*-

from collections import defaultdict
from xml.sax import handler
from xml.sax.saxutils import escape

class eSearchResultHandler(handler.ContentHandler):
   """Parse PubMed eSearch XML results. Update a dictionary
   in place that has to be provided upon initialization."""

   ROOT = ('eSearchResult',)
   # Fields of interest.
   FIELDS = {
      ROOT + ('Count',): 'count',
      ROOT + ('QueryKey',): 'query_key',
      ROOT + ('WebEnv',): 'WebEnv'
   }

   def __init__(self, termdict):
      self._stack = []
      self._errors = False
      self.data = ''
      # 'termdict' passed by reference.
      self.termdict = termdict

   def startElement(self, name, attrs):
      self.data = ''
      self._stack.append(name)
      if name == 'ErrorList':
         self._errors = True
         self.termdict['errors'] = []

   def endElement(self, name):
      if name == 'ErrorList': self._errors = False

      field = self.FIELDS.get(tuple(self._stack))
      # Update the given field by list-append.
      if field:
         self.termdict[field] = self.data
      if self._errors:
         # Within the "ErrorList" node, append key-value tuple
         # with the end of the stack and the data, like
         # ([node, child, grandchild], data). For example:
         # ([u'PhraseNotFound'], u'2011/11/28[crdt]')
         self.termdict['errors'].append(
               (self._stack[-1:], self.data.strip())
         )

      self._stack.pop()
      self.data = ''

   def characters(self, data):
      self.data += data


class eFetchResultHandler(handler.ContentHandler):
   """Parse PubMed eFetch XML results. Update in place a list of
   JSON-like documents (passed by reference). This format is flexible
   (if formating is needed) and can be easily serialized to text
   format.

   Each abstract is stored into a JSON-like document:
   {
       'pmid': '12345678',
       'journal': 'Journal name',
       'pubdate': 'Jan 01 2001',
       'title': 'Article title',
       'author_list': [ 'A First', 'B Second', ..., 'Z Last' ],
       'authors': 'A First, B Second, ..., Z Last',
       'text': 'Abstract text.'
   }

   NB: By default, abstracts without a text are not returned.
   In order to get them anyway, pass 'return_empty=True' to the
   constructor."""

   ROOT = ('PubmedArticleSet', 'PubmedArticle', 'MedlineCitation')
   ARTICLE = ROOT + ('Article',)
   JOURNAL = ARTICLE + ('Journal',)
   # Fields of interest.
   FIELDS = {
      ROOT + ('PMID',): 'pmid',
#     JOURNAL + ('JournalIssue', 'Volume'): 'vol',
#     JOURNAL + ('JournalIssue', 'Issue'): 'issue',
      JOURNAL + ('JournalIssue', 'PubDate', 'Year'): 'year',
      JOURNAL + ('JournalIssue', 'PubDate', 'Month'): 'month',
      JOURNAL + ('JournalIssue', 'PubDate', 'Day'): 'day',
      JOURNAL + ('Title',): 'jrnl',
      ARTICLE + ('ArticleTitle',): 'title',
#     ARTICLE + ('Pagination', 'MedlinePgn'): 'page',
      ARTICLE + ('Abstract', 'AbstractText'): 'text',
      ARTICLE + ('AuthorList', 'Author', 'LastName'): 'name',
#     ARTICLE + ('AuthorList', 'Author', 'ForeName'): 'forename',
      ARTICLE + ('AuthorList', 'Author', 'Initials'): 'intls',
#     ARTICLE + ('Language',): 'language',
#     ARTICLE + ('PublicationTypeList', 'PublicationTypes'): 'pubtypes',
#     ROOT + ('MeshHeadingList', 'MeshHeading', 'DescriptorName'): 'mesh'
   }

   def __init__(self, abstr_list, return_empty=False):
      """Initialize a 'defaultdict' of collected terms, and
      _stack/data variables used for data collection."""

      # Call the super constructor.
      handler.ContentHandler.__init__(self)

      self.return_empty = return_empty
      # 'defaultdict' is quite handy here (see below).
      self._dict = defaultdict(list)
      self._stack = []
      self.data = ''
      # 'abstr_list' passed by reference.
      self.abstr_list = abstr_list

   def startElement(self, name, attrs):
      self.data = ''
      self._stack.append(name)
      if name == 'PubmedArticle': self._dict.clear()

   def endElement(self, name):

      if name == 'PubmedArticle': self.json_wrap()

      field = self.FIELDS.get(tuple(self._stack))
      # Update the given field by list-extension
      # NB: it works because '_dict' is a  'defaultdict'.
      if field:
         self._dict[field].extend([self.data.strip()])

      self._stack.pop()
      self.data = ''

   def characters(self, data):
      self.data += data


   def json_wrap(self):
      """Wrap an abstract to JSON-like document."""

      # Abstracts without a text are discarded by default.
      if not self.return_empty and not self._dict.has_key('text'):
         return

      abstr = {}

      # Define fields 'pmid', 'journal', 'pubdate', 'title', 'authors'
      # and 'text'. NB: '_dict' is a default dict, so by the use of
      # 'join()' the attributes are always defined, but possibly empty.
      # Joining on "_PARSE_ERROR_" the fields that are supposed to
      # be unique helps reveal mis-formatted abstract models.

      abstr['pmid'] = '_PARSE_ERROR_'.join(self._dict['pmid'])
      abstr['journal'] = '_PARSE_ERROR_'.join(self._dict['jrnl'])

      # NB: I do not implement a datetime.datetime object because
      # some PubMed pubdates specify only the month and the year.
      # Field 'pubdate' looks like "Jan 1 2001".
      abstr['pubdate'] = ' '.join(
         self._dict['month'] \
         + self._dict['day'] \
         + self._dict['year']
      )
      abstr['title'] = '_PARSE_ERROR_'.join(self._dict['title'])
      # Field 'authors' looks like ["A First", "B Second", ..., "Z Last"]
      abstr['author_list'] = [
            ' '.join(intls_name) \
            for intls_name in zip(self._dict['intls'], self._dict['name'])
      ]
      # Format authors to a single line of text.
      abstr['authors'] = ', '.join(abstr['author_list'])
      abstr['text'] = ''.join(self._dict['text'])

      # Append (list is passed by reference).
      self.abstr_list.append(abstr)
