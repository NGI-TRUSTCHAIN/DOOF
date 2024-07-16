#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024
import code
import sys

from common.python.error import DopError
from doof_python_apis import DOOFPythonAPIs
from events import dop_events


# We want to inject some preset variables ("names" in Python)
# Grab the locals(), add our own to it
local_names = locals()
local_names['ver'] = '2.0'
apis = DOOFPythonAPIs()
conf_file=sys.argv[1]
err = apis.init(conf_file)
if err.isError():
    print("Error in initializing client with supplied configuration file")
    sys.exit()

local_names['apis'] = apis

banner: str = "Python client"
#console = code.interact(local=local_names, readfunc=reader)
console = code.interact(local=local_names)


