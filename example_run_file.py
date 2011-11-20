#!/usr/bin/python
# set encoding=utf-8
#
# usage: python -m pyxdebug example_run_file.py

class Fib(object):
    def __init__(self):
        pass

    def calc(self, n):
        if n<3:
            return 1
        return self.calc(n - 1) + self.calc(n - 2)

fib = Fib()
result = fib.calc(6)

print "result: %d\n" % result
