# -*- coding:utf-8 -*-

import os
import json
import unittest
from xml.sax import make_parser

import utils

import addlibdir
import eUtils
import SAXmed

class Test_eUtils(unittest.TestCase):
   def test_get_hit_count_or_raise(self):
      # The following should not raise any exception and return
      # many hits (there were about 3620 records added to PubMed on
      # April 13, 2013 but the exact number can change).
      counts = eUtils.get_hit_count_or_raise(u'2013/04/13[crdt]')
      self.assertTrue(counts > 0)

   def test_robust_eSearch_query(self):
      """The exceptions are fired by 'get_hit_count'.
      This also tests 'SAXmed.eSearchResultHandler'."""
      # Check that exceptions are raised for non PubMed vocabulary.
      with self.assertRaises(eUtils.PubMedException) as cm:
         eUtils.robust_eSearch_query(u'not_a_pub_med_term')
      msg = cm.exception.message
      target = [([u'PhraseNotFound'], u'not_a_pub_med_term')]

      # Check that exceptions are raised for empty terms.
      # There is no record created in PubMed on Sunday April 14, 2013.
      with self.assertRaises(eUtils.PubMedException) as cm:
         eUtils.robust_eSearch_query(u'2013/04/14[crdt]')
      msg = cm.exception.message
      target = [([u'PhraseNotFound'], u'2013/04/14[crdt]')]
      self.assertEqual(msg, target)

      # Check that the following raises NoHitException.
      # Some of my articles are referenced in PubMed, there are
      # some entries created on Saturday April 13, 2013, but I
      # have no articled referenced on that date.
      with self.assertRaises(eUtils.NoHitException):
         no_hit_query = u'filion+g[author]+AND+2013/04/13[crdt]'
         eUtils.robust_eSearch_query(no_hit_query)

      # There are record created in PubMed on Satudray April 13, 2013.
      # The following should not raise any exception.
      eUtils.robust_eSearch_query(u'2013/04/13[crdt]')

   def test_fetch_ids(self):
      """This also tests 'SAXmed.eFetchResultHandler'."""
      (abs1, abs2) = eUtils.fetch_ids(['22180407', '23580981'])
      target_title1 = u'Update on PARP1 inhibitors in ovarian cancer.'
      target_title2 = u'Replication clamps and clamp loaders.'
      self.assertEqual(abs1['title'], target_title1)
      self.assertEqual(abs2['title'], target_title2)

   def test_fetch_abstr(self):
      """This also tests 'SAXmed.eFetchResultHandler'."""
      query = u'nature[journal]+AND+2012/12/21[crdt]'
      target_ids = [
         u'23254940', u'23254938', u'23254936', u'23254935',
         u'23254933', u'23254931', u'23254930', u'23254929'
      ]
      ab_list = eUtils.fetch_abstr(query)
      self.assertEqual(len(ab_list), 8)
      self.assertEqual([ab['pmid'] for ab in ab_list], target_ids)

class Test_SAXmed(unittest.TestCase):
   def test_eSearchResultHandler(self):
      """Test the parsing of a typical eSearch result in xml format."""
      qdict = {}
      parser = make_parser()
      parser.setContentHandler(SAXmed.eSearchResultHandler(qdict))
      with open(os.path.join('test', 'eSearch_result.xml')) as f:
         parser.parse(f)
      with open(os.path.join('test', 'target_eSearch_result.json')) as f:
         target = json.load(f)
      self.assertEqual(qdict, target)

   def test_eFetchResultHandler(self):
      """Test the parsing of a typical eFetch result in xml format."""
      ab_list = []
      parser = make_parser()
      parser.setContentHandler(SAXmed.eFetchResultHandler(ab_list))
      with open(os.path.join('test', 'eFetch_result.xml')) as f:
         parser.parse(f)
      with open(os.path.join('test', 'target_eFetch_result.json')) as f:
         target = json.load(f)
      self.assertEqual(ab_list, target)


class TestData:
   def put(self):
      return True

class Test_utils(unittest.TestCase):
   def test_try_to_update_term(self):
      """Test the term update routine."""
      data = TestData()
      term = 'chromatin[all]\n+AND+nature[journal]'
      success = utils.try_to_update_term(data, term)
      self.assertTrue(success)


if __name__ == '__main__':
   unittest.main()
