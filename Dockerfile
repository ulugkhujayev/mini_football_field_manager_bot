FROM python:3.9-slim


WORKDIR /app


COPY requirements.txt requirements.txt


RUN pip install --no-cache-dir -r requirements.txt


COPY . .


ENV API_TOKEN=your_api_token
ENV ADMIN_IDS=your_admin_ids
ENV PHONE_NUMBER=your_phone_number


EXPOSE 8443


CMD ["python", "bot.py"]

