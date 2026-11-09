# Book&Ride - Unit 05 - build the package ONCE (wheel), then install and test
# that wheel in a clean image: what is tested is exactly what would be published.
FROM python:3.12-slim AS build
WORKDIR /src
COPY . .
RUN pip wheel --no-deps --wheel-dir /dist .          # -> bookandride_pricing-1.0.0-py3-none-any.whl

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1
COPY --from=build /dist /dist
COPY tests /tests
RUN pip install --no-cache-dir /dist/*.whl pytest     # the WHEEL, not the source folder
RUN useradd --create-home app
USER app
WORKDIR /tests
CMD ["sh", "-c", "ls /dist && pip show bookandride-pricing | head -3 && bookandride-price 1500 && python -m pytest -q /tests -p no:cacheprovider"]
