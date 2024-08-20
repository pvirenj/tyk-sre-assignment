FROM python:3.10

WORKDIR /sretool

COPY ./python/ /sretool

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

ENTRYPOINT ["python", "main.py"]
#CMD [ "main.py --kubeconfig '/home/vagrant/.kube/config' --address ':8080'" ]
