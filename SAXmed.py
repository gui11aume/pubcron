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
   """Parse PubMed eFetch XML results. Update a list in place
   that has to be provided upon initialization.

   NB: By default, abstracts without a text are not returned.
   Initialize the instance with 'return_empty=True' to get them."""

   class Abstr:
      """Only a namespace for this module. But Abstr isntances
      can be sorted based on scores, if given as attributes."""

      def __lt__(self, other):
         return self.score < other.score


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

   def __init__(self, Abstr_list, return_empty=False):
      """Initialize a 'defaultdict' of collected terms, and
      _stack/data variables used for data collection."""

      # Call the super constructor.
      handler.ContentHandler.__init__(self)

      self.return_empty = return_empty
      # 'defaultdict' is quite handy here (see below).
      self._dict = defaultdict(list)
      self._stack = []
      self.data = ''
      # 'Abstr_list' passed by reference.
      self.Abstr_list = Abstr_list

   def startElement(self, name, attrs):
      self.data = ''
      self._stack.append(name)
      if name == 'PubmedArticle': self._dict.clear()

   def endElement(self, name):

      if name == 'PubmedArticle': self.wrap()

      field = self.FIELDS.get(tuple(self._stack))
      # Update the given field by list-extension
      # NB: it works because '_dict' is a  'defaultdict'.
      if field:
         self._dict[field].extend([self.data.strip()])

      self._stack.pop()
      self.data = ''

   def characters(self, data):
      self.data += data


   def wrap(self):
      """Wrap an instance  of Abstr with few attributes."""

      # Abstracts without a text are discarded by default.
      if not self.return_empty and not self._dict.has_key('text'):
         return

      # Define attributes 'pmid', 'journal', 'pubdate', 'title',
      # 'authors' and 'text'.
      abstr = self.Abstr()

      # NB: '_dict' is a default dict, so by the use of 'join()'
      # the attributes are always defined, but possibly empty.
      abstr.pmid = ':'.join(self._dict['pmid'])
      abstr.journal = ''.join(self._dict['jrnl'])
      abstr.pubdate = ' '.join(
         self._dict['month'] + self._dict['day'] + self._dict['year']
      )
      abstr.title = ''.join(self._dict['title'])
      abstr.authors = ', '.join([
            ' '.join(a) \
            for a in zip(self._dict['intls'], self._dict['name'])
      ])
      abstr.text = ''.join(self._dict['text'])

      self.Abstr_list.append(abstr)
