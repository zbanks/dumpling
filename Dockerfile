FROM python:alpine

COPY ./requirements.txt /app/requirements.txt
RUN pip3 install -r /app/requirements.txt

COPY dumpling.py /app/

WORKDIR app
ENTRYPOINT ["gunicorn"]
CMD ["dumpling:app"]
