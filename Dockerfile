FROM python:3
COPY run.py .
COPY requirements.txt .
COPY Head.yml .
COPY Rule.yml .
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
CMD ["python", "./run.py"]