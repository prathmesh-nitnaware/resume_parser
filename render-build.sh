#!/usr/bin/env bash

# Install requirements
pip install -r requirements.txt

# Install spaCy model
python -m spacy download en_core_web_sm
