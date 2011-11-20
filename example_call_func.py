#!/usr/bin/python
# set encoding=utf-8
#
# usage: python example_call_func.py

from pyxdebug import PyXdebug

class Fib(object):
    def __init__(self):
        pass

    def calc(self, n):
        if n<3:
            return 1
        return self.calc(n - 1) + self.calc(n - 2)

xd = PyXdebug()
#xd.collect_imports = 1
#xd.collect_params = 0
#xd.collect_return = 0
#xd.collect_assignments = 0

fib = Fib()
result = xd.run_func(fib.calc, 6)

print "result: %d\n" % result
print xd.get_result()
