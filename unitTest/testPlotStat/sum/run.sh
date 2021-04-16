#!/bin/bash

valgrind --trace-children=yes --tool=verrou ./sum.py > $1/out 2>&1
