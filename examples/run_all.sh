
cp ../tests/bird_jsc.ms? .

python fdsnws_mseed3.py && \
python ginormous_ms3.py && \
python minimal_rw_mseed3.py && \
python miniseed2to3.py bird_jsc.ms2 && \
python read_miniseed2.py bird_jsc.ms2 && \
python readwrite_miniseed3.py && \
python dedup_miniseed2.py  -f bird_jsc.ms2 && \
python long_sid.py && \
python sourceid.py && \
rm -f bird_jsc.ms? converted.ms3 dedup_bird_jsc.ms2
