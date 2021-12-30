FROM ghcr.io/foreseeti/securicad-parser

ADD dist/android-parser-*.tar.gz .
RUN mv android-parser-*/* ./
RUN pip install --force-reinstall --ignore-installed --upgrade --no-index --no-deps wheels/*.whl
RUN rm -rf android-parser-*/
RUN rm -rf wheels/