FROM balenalib/raspberrypi3-alpine-python:3.8-latest-build
RUN pip install pyserial
RUN pip install requests
COPY main.py main.py
CMD python main.py