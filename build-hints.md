
# build/release
```
conda env remove -n simplemseed
conda create -n simplemseed python=3.10 pytest hatch pip -y
conda activate simplemseed
hatch clean && hatch build
pip3 install dist/simplemseed-*-py3-none-any.whl --force-reinstall
hatch test

```

for testing, use code in current directory so updates on edit:
```
pip install -v -e .
```

Hints on publish:
https://packaging.python.org/en/latest/tutorials/packaging-projects/

```
# note may need to remove ~/Library/Application\ Support/hatch
# if see error "No module named pip" after changing pyver
pyver=3.10
conda create -n do_release hatch pytest pylint requests python=$pyver -y
conda activate do_release
/bin/rm -f dist/*
hatch clean && hatch build && pip install dist/simplemseed*.whl
hatch test
pylint src/simplemseed | grep -v snake_case | grep -v docstring | grep -v line-too-long | grep -v R091

# test multiple version of python
hatch test --all --parallel
cd examples ; ./run_all.sh ; cd ..
# update release/version in docs/source/conf.py
# sphinx and
# pip install sphinx-autodoc2
conda activate sphinx
cd docs ; make clean && make html && open build/html/index.html && cd ..
conda activate do_release
git status
git tag -a -m "version to 0.5.0" v0.5.0
git push
# first time
# hatch publish -u __token__ --auth <token>
hatch publish

conda deactivate
conda env remove -n do_release -y
```

Then release simplemseed obspy plugin.
