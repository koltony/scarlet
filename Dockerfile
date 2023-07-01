FROM python:3.11.4

WORKDIR /scarlet

RUN apt-get update
RUN mkdir ./scarlet


COPY . /scarlet

EXPOSE 8000
RUN pip install -r requirements.txt
RUN export PYTHONPATH=/scarlet/scarlet/

RUN dir

CMD ["python", "./scarlet/main.py"]