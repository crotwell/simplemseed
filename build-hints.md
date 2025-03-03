
# build/release
```
conda create -n simplemseed python=3.9
conda activate simplemseed
python3 -m pip install --upgrade hatch
python3 -m pip install --upgrade pytest
hatch clean && hatch build
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
pyver=3.9
conda create -n do_release hatch pytest pylint requests python=$pyver -y -q
conda activate do_release
/bin/rm -f dist/*
hatch clean && hatch build && pip install dist/simplemseed*.whl
pytest && pylint src/simplemseed | grep -v snake_case | grep -v docstring | grep -v line-too-long | grep -v R091

cd tests ; ./pytest_many_python.sh ; cd ..
cd examples ; ./run_all.sh ; cd ..
# update release/version in docs/source/conf.py
# sphinx and
# pip install sphinx-autodoc2
conda activate sphinx
cd docs ; make clean && make html && open build/html/index.html ; cd ..
conda activate do_release
git status
git tag -a -m "version to 0.4.4" v0.4.4
git push
# first time
# hatch publish -u __token__
hatch publish

conda deactivate
conda env remove -n do_release -y
```
