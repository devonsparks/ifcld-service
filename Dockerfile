FROM python:3.10-alpine 


WORKDIR /service

COPY . .

RUN pip3 install -r requirements.txt

EXPOSE 5000

# TODO: front with an ASGI web server
CMD ["python3", "service.py"]