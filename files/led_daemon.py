#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diem vao cua daemon den LED. Goi bang: ./launch.sh --led-daemon

Logic nam trong rh/leddaemon.py de test import duoc; file nay chi la vo."""

import sys

from rh.leddaemon import main

if __name__ == "__main__":
    sys.exit(main())
