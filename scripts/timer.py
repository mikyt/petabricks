#!/usr/bin/env python
import time
import subprocess
import sys

cmd_line = sys.argv[1:]

start = time.time()
result = subprocess.call(cmd_line)
end = time.time()

f = open("tmp_time", "w")
f.write(str(end-start))
f.close()

sys.exit(result)