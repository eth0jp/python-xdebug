#!/usr/bin/python
# set encoding=utf-8
#
# usage: python example_call_func.py

from pyxdebug import PyXdebug

class TestCls1(object):
   def __init__(self):
       self.num = 0

   def add(self):
       self.num += 1

   def loop(self, count=10):
       for i in xrange(count):
           import wave, string
           self.add()


xd = PyXdebug()
#xd.collect_imports = 1
#xd.collect_params = 0
#xd.collect_return = 0
#xd.collect_assignments = 0

tc = TestCls1()
xd.run_func(tc.loop)
print xd.get_result()
