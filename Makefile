.PHONY: build up down logs dev

build:
	docker compose up --build

up:
	docker compose up

down:
	docker compose down

logs:
	docker compose logs -f

dev:
	docker compose up --build --force-recreate
