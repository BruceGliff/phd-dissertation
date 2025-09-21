#!/bin/sh

# 1. Установка Docker и Git
# skip
# echo "==> Installing Docker and Git packages"

# 2. Установка DockerTex
echo "==> Downloading and updating docker image"
sg docker -c "docker build -t raabf/texstudio-versions:latest ."

# 3. Настройка DockerTex
## 3.1 Клонирование репозитория
echo "==> Downloading dockertex"
DOWNLOADS_DIR=$(pwd)/external
if [ ! -d $DOWNLOADS_DIR/dockertex ]; then
  mkdir -p $DOWNLOADS_DIR
  cd $DOWNLOADS_DIR && git clone https://github.com/raabf/dockertex.git && cd -
fi


DST_DIR=$(pwd)/scripts
mkdir -p $DST_DIR
mkdir -p $DST_DIR/desktop
mkdir -p $DST_DIR/bin
echo "==> Registering dockertex commands and shortcuts"
## 3.2 добавление команд dockertex и dockertexstudio в папку scripts/bin
$DOWNLOADS_DIR/dockertex/install.sh --app-prefix $DST_DIR/desktop --bin-prefix $DST_DIR/bin --menu-volume DockerTexLive --menu-tag latest

echo "==> Fixing start of TexStudio"
## 3.3 Исправление для запуска TexStudio
sed -i '/--net=host\ \\/d' $DST_DIR/bin/dockertexstudio
sed -i '10i xhost local:root' $DST_DIR/bin/dockertexstudio
sed -i "s|HOME=/home/|HOME=$(pwd)|g; s|--workdir=/home/|--workdir=$(pwd)|g" $DST_DIR/bin/dockertexstudio
sed -i '/image_tag="${DOCKERTEX_DEFAULT_TAG}"/i DOCKERTEX_DEFAULT_TAG=latest' $DST_DIR/bin/dockertexstudio
sed -i '/image_tag="${DOCKERTEX_DEFAULT_TAG}"/i DOCKERTEX_DEFAULT_TAG=latest' $DST_DIR/bin/dockertex
sed -i "s|HOME=/home/|HOME=$(pwd)|g" $DST_DIR/bin/dockertex

