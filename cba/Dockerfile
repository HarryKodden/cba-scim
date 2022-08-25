
FROM python:3

WORKDIR /opt

COPY SCIM-Notify-demo/app app
COPY sync/SCIM.py app/SCIM.py
COPY cba/cba.py app/cba.py

RUN pip install -r app/requirements.txt

CMD ["python3", "app/cba.py"]
