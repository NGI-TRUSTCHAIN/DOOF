#   SPDX-License-Identifier: Apache-2.0
# © Copyright Ecosteer 2024
"""
Minimalistic implementation of platform's thread control

"""

import sys
try:
    from threading import Event, Thread
    from common.python.dop_stop_event import DopStopEvent
except ImportError: 
    from common.dop_stop_event_mpy import DopStopEvent






    
