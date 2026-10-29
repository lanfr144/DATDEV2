#!/usr/bin/env python
"""Django command-line utility (python manage.py runserver / migrate / test)."""
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "booksite.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
