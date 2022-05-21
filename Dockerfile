FROM python:alpine
RUN pip3 install flask gunicorn
COPY dumpling.py /app
COPY dumpling.db /app
WORKDIR app
ENTRYPOINT ["gunicorn"]
CMD ["dumpling:app"]
