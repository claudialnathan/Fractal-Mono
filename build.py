#!/usr/bin/env python3
"""Build Fractal Mono from its editable sources."""
from pathlib import Path
import argparse,subprocess,sys
from sources import build,validate,book,release

ROOT=Path(__file__).resolve().parent

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true',help='also run the source, shaping, variation and export tests');args=parser.parse_args()
 validate.validate_source();build.main();validate.main();book.main();release.main()
 if args.check:subprocess.run([sys.executable,'-m','unittest','discover','-s',str(ROOT/'.github/tests')],cwd=ROOT,check=True)

if __name__=='__main__':main()
