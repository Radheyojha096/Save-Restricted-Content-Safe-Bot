FROM python:3.10-slim-bullseye
RUN apt update && apt upgrade -y
RUN apt-get install -y git curl ffmpeg wget bash neofetch
COPY requirements.txt .

RUN pip3 install wheel
RUN pip3 install --no-cache-dir -U -r requirements.txt
WORKDIR /app
COPY . .

CMD ["python3", "app.py"]


