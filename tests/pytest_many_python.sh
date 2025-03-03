#!/bin/zsh

# runs pytest under several versions of python using conda

source ~/.zshrc

cd ..

for ver in 3.9 3.10 3.11 3.12 3.13 ; do
  conda create -n pytest_$ver hatch pytest python=$ver -y -q
  conda activate pytest_$ver
  /bin/rm -f dist/*
  hatch clean
  hatch build
  if [ ! -f "dist/simplemseed-*-py3-none-any.whl"]; then
    echo Fail to build $ver
    exit 2
  fi
  pip install dist/simplemseed-*-py3-none-any.whl
  if pytest ; then
    echo python $ver ok
  else
    echo Fail!
    exit 1
  fi

  conda deactivate
  conda env remove -n pytest_$ver -y
  echo OK $ver
done;

cd tests
