
FROM python:3.11-slim as base

ENV STAC_API_URL null

# Any python libraries that require system libraries to be installed will likely
# need the following packages in order to build
RUN apt-get update && apt-get install -y build-essential git

RUN git clone https://github.com/cedadev/stac-generator-example.git

WORKDIR /populator

COPY ./requirements.txt .

RUN pip install -r requirements.txt

RUN apt install wget
RUN wget https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh
RUN chmod +x wait-for-it.sh

COPY . .

CMD ["/bin/sh", "-c", "./populate.sh"]
