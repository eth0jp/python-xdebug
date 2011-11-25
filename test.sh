#!/bin/bash

python test_pyxdebug.py --with-coverage --with-xunit
/usr/bin/env coverage xml
