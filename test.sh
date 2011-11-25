#!/bin/bash

python test_pyxdebug.py --with-coverage --with-xunit
/usr/local/bin/coverage xml
