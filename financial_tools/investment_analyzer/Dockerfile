FROM python:3.12-slim

WORKDIR /app

COPY ../../financial_tools/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY ../../financial_tools ./financial_tools

EXPOSE 8000

CMD ["uvicorn", "financial_tools.investment_analyzer.server:app", "--host", "0.0.0.0", "--port", "8000"]
