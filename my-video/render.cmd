@echo off
set PATH=%PATH%;C:\Users\muzhi\AppData\Local\ffmpegio\ffmpeg-downloader\ffmpeg\bin
npx --yes hyperframes@0.6.20 render %*
