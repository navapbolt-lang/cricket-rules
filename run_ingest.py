import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))
from scripts.ingest_pdfs import ingest_pdfs

ingest_pdfs()
