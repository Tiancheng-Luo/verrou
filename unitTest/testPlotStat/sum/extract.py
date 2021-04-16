#!/usr/bin/env python3
import sys
blockSize=1

for line in open(sys.argv[1]+"/out"):    
    if line.startswith("sum"):
#        print(line.split()[1]) #value
        print(line.split()[3]) #error
        sys.exit(0)
sys.exit(42)
    
