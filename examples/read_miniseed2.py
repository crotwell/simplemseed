import simplemseed
import sys
import os

def readMiniseed(ms2filename):
    with open(ms2filename, "rb") as inms2:
        for ms2rec in simplemseed.readMiniseed2Records(inms2):
            print(ms2rec.summary())


def main():
    for a in sys.argv[1:]:
        if os.path.exists(a):
            readMiniseed(a)


if __name__ == "__main__":
    main()
