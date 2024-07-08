RUN pip install -r requirements.txt
CMD ["python", "main.py"]
docker build -t <Echo> .
docker run -d --name Main <Echo>
