#!/usr/bin/python
# set encoding=utf-8
#
# usage: python -m pyxdebug example_run_file.py

class TestCls1(object):
   def __init__(self):
       self.num = 0

   def add(self):
       self.num += 1

   def loop(self, count=10):
       for i in xrange(count):
           import wave, string
           self.add()


tc = TestCls1()
tc.loop()
