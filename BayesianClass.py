# -*- coding: utf-8 -*-
import re

# Here-list of title stop-words.
stopw = ('and', 'the', 'of', 'a', 'in', 'to', 'at', 'by',
         'as', 'with', 'via', 'is', 'are', 'from', 'for',
         'an', 'into')

def to_words(string):
   string = string.lower().replace('-', ' ')
   # Remove punctuation.
   for sign in (':', '?', '.', ',', ';'):
      string = string.replace(sign, '')
   # Remove isolated numbers (after replacing dash by space).
   string  = re.sub(' [0-9]+ ', ' ', string)
   # Split, remove stopwords.
   return [w for w in string.split(' ') if not w in stopw]
