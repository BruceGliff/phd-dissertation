FROM raabf/texstudio-versions:latest

# Auto install russian language
RUN apt-get update && \
    apt-get install -y \
      curl \
      hunspell \
      hunspell-ru \
      hunspell-en-us

RUN curl -L https://extensions.openoffice.org/en/download/5292 > /tmp/ru_dict.zip && \
unzip -o /tmp/ru_dict.zip -d /usr/share/texstudio

