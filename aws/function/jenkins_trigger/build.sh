#!/bin/bash
set -e

zip jenkins_trigger.zip lambda_function.py

mv -f jenkins_trigger.zip ../../jenkins_trigger.zip
