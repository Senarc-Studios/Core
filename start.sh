#!/bin/bash
uvicorn main:app --reload --host 127.0.0.1 --workers 2 --port 2000
