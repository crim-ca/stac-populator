
FROM python:3.11-slim as base

# Any python libraries that require system libraries to be installed will likely
# need the following packages in order to build
RUN apt-get update && apt-get install -y build-essential git

RUN git clone https://github.com/cedadev/stac-generator-example.git

COPY ./requirements.txt /

RUN pip install -r requirements.txt

RUN apt install wget
RUN wget https://github.com/vishnubob/wait-for-it/blob/master/wait-for-it.sh

COPY . /populator

CMD ["ls"]
