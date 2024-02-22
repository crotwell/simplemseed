from simplemseed import readMiniseed2Records, mseed2to3
import sys

def convert(ms2filename, ms3filename):
    with open(ms3filename, "wb") as outms3:
        with open(ms2filename, "rb") as inms2:
            for ms2rec in readMiniseed2Records(inms2):
                ms3rec = mseed2to3(ms2rec)
                print(ms3rec.details())
                outms3.write(ms3rec.pack())


def main():
    for a in sys.argv[1:]:
        convert(a, "converted.ms3")


if __name__ == "__main__":
    main()
