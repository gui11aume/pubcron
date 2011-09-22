# -*- coding: utf-8 -*-
import re

# Here-list of title stop-words.
stopw = ('and', 'the', 'of', 'a', 'in', 'to', 'at', 'by',
         'as', 'with', 'via', 'is', 'are', 'from', 'for',
         'an', 'into', 'non', 'not', 'no')

def to_words(string):
   string = string.lower().replace('-', ' ')
   # Remove punctuation.
   for sign in (':', '?', '.', ',', ';'):
      string = string.replace(sign, '')
   # Remove isolated numbers (after replacing dash by space).
   string  = re.sub(' [0-9]+ ', ' ', string)
   # Split, remove stopwords.
   return [w for w in string.split(' ') if not w in stopw]

def update_score(abstr_list, rlvt, irlvt, pos, neg):
   for abstr in abstr_list:
      words = to_words(abstr.title)
      abstr.words = ':'.join(words)
      score = 0.1 # Fraction relevant abstracts
      try:
         for w in words:
            score *= pos.count(w)*(irlvt+1) / neg.count(w)*(rlvt+1)
         abstr.score = '%.2f' % score
      except ZeroDivisionError:
         abstr.score = '*'


