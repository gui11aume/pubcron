# -*- coding: utf-8 -*-

# The following code is inspired from the nltk module (which
# I do not import because I use only a tiny fraction of it).

import re
import logging
from math import log, sqrt
from porter import PorterStemmer
from collections import defaultdict

## -----------------------    DATA    ------------------------ ##
stopw = set(('a', 'about', 'again', 'all', 'almost', 'also',
   'although', 'alway', 'among', 'an', 'and', 'anoth', 'ani',
   'are', 'as', 'at', 'be', 'becaus', 'been', 'befor', 'between',
   'both', 'but', 'by', 'can', 'could', 'did', 'do', 'doe',
   'done', 'due', 'dure', 'each', 'either', 'enough', 'especi',
   'etc', 'for', 'found', 'from', 'further', 'had', 'ha', 'have',
   'here', 'how', 'howev', 'i', 'if', 'in', 'into', 'is', 'it',
   'itself', 'just', 'kg', 'km', 'made', 'mainli', 'make', 'may',
   'mg', 'might', 'ml', 'mm', 'most', 'mostli', 'must', 'nearli',
   'neither', 'no', 'non', 'nor', 'not', 'of', 'often', 'on',
   'our', 'overal', 'perhap', 'pmid', 'quit', 'rather', 'realli',
   'regard', 'seem', 'seen', 'sever', 'should', 'show', 'shown',
   'significantli', 'sinc', 'so', 'some', 'such', 'than', 'that',
   'the', 'their', 'them', 'then', 'there', 'therefor', 'these',
   'they', 'thi', 'those', 'through', 'thu', 'to', 'upon', 'use',
   'variou', 'veri', 'via', 'wa', 'we', 'were', 'what', 'when',
   'which', 'while', 'with', 'within', 'without', 'would'))


class ShortFloat(float):
   """Subclass of float for short JSON serialization. This keeps
   the number of digits to 3 fo tfidf and saves a lot of disk
   space."""
   def __repr__(self):
      return '%.3f' % self

def preprocess(txt, stem=PorterStemmer().stem):
   # NB: The memory usage is about 2 Mb per 100 PubMed abstracts.
   # Lower-case and tokenize the texts, also remove numbers.
   if not txt:
      logging.warn('got an empty txt in `preprocess`')
   txt = re.sub(
      # 2. Remove numbers.
         ' [0-9]+ ',
         ' ',
      re.sub(
      # 1. Replace split chars.
         '[-)(!?}{:;,\.\[\]]',
         ' ',
         txt
      # 3. Split on spaces.
      )).lower().split()
   # Stem the tokens and remove stop words.
   stems = [w for w in (stem(w) for w in txt) if not w in stopw]
   if not stems:
      logging.warn('empty stems in `preprocess`')
   return stems


def compute_from_texts(texts, aux=[]):
   """Collection of term/tf-idf dictionaries, where terms are
   lower-cased and stemmed by the Porter stemmer.The parameter
   'aux' is a pre-processed part of the corpus that is used only
   for computing idf (skip tf)."""

   texts = [preprocess(txt) for txt in texts]

   # Compute term and document frequencies.
   docf = defaultdict(int)
   termf_dicts = []

   for txt in texts:
      # Count words in text.
      wcounts_for_this_text = defaultdict(int)
      for word in txt:
         wcounts_for_this_text[word] += 1
      # Compute term frequencies, update doc frequencies.
      tf_for_this_text = {}
      total = float(len(txt))
      for word in wcounts_for_this_text:
         tf_for_this_text[word] = wcounts_for_this_text[word] / total
         docf[word] += 1
      # Store term frequencies in 'termf_dicts'.
      termf_dicts.append(tf_for_this_text)

      # Add the terms in auxiliary corpus to doc frequencies.
      for txt in aux:
         for word in set(txt): docf[word] += 1

   # Last loop to compute tf-idf scores.
   corpus_size = float(len(texts) + len(aux))
   tfidf_dicts = []
   for this_tf in termf_dicts:
      this_tfidf = {}
      for w in this_tf:
         this_tfidf[w] = ShortFloat(this_tf[w]*log(corpus_size/docf[w]))

      tfidf_dicts.append(this_tfidf)

   return tfidf_dicts


def cosine(tfidf_dict_a, tfidf_dict_b):
   """Compute the cosine similarity between two dictionaries
   of tfidf scores."""

   numerator = sum([
       tfidf_dict_a[w] * tfidf_dict_b[w] \
       for w in set(tfidf_dict_a).intersection(tfidf_dict_b)
   ])
   denominator = sqrt(
       sum([v**2 for v in tfidf_dict_a.values()]) * \
       sum([v**2 for v in tfidf_dict_b.values()])
   )
   try:
      return numerator / denominator
   except ZeroDivisionError:
      # DEBUG
      logging.warn('cosine error (1):' + str(tfidf_dict_a))
      logging.warn('cosine error (2):' + str(tfidf_dict_b))
      return None
