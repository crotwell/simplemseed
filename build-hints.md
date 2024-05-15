
# build/release
```
conda create -n simplemseed python=3.9
conda activate simplemseed
python3 -m pip install --upgrade hatch
pytest
hatch clean
hatch build
pip3 install dist/simplemseed-*-py3-none-any.whl --force-reinstall
pytest
```

for testing, use code in current directory so updates on edit:
```
pip install -v -e .
```

Hints on publish:
https://packaging.python.org/en/latest/tutorials/packaging-projects/

```
python3 -m pip install --upgrade hatch
hatch clean && hatch build
pytest && pylint src/simplemseed | grep -v snake_case | grep -v docstring | grep -v line-too-long

cd examples ; ./run_all.sh ; cd ..
# update release/version in docs/source/conf.py
cd docs ; make clean && make html && open build/html/index.html ; cd ..
git status
git push
hatch publish
```
